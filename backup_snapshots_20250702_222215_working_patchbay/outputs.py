from PyQt6.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QVBoxLayout, QScrollArea
import alsa_backend
from mixer_channels import build_output_map, OUTPUT_TABS
from mixer_widgets import MixerGroupWidget, OutputFaderWidget, StereoPairStrip, ChannelStrip
from alsa_polling import AlsaPollingWorker
from patchbay import PatchbayView
from typing import cast

class OutputsTabs(QWidget):
    def __init__(self, card_index=1):
        super().__init__()
        self.tabs = QTabWidget()
        v = QVBoxLayout(self)
        v.addWidget(self.tabs)
        self.setLayout(v)

        # Store ChannelStrips per tab (list of lists)
        self.tab_channel_strips = []

        out_map, func_map = build_output_map(alsa_backend, card_index=1)
        canonical_order = ["Mic", "Line", "ADAT", "PCM"]

        for pair in OUTPUT_TABS:
            tab = QWidget()
            tab_layout = QHBoxLayout(tab)

            # Collect strips for this tab
            tab_strips = []

            # Left: All groups in a scrollable row
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            strip = QWidget()
            h = QHBoxLayout(strip)
            h.setSpacing(50)

            for group in canonical_order:
                group_pairs = out_map[pair].get(group, [])
                if group_pairs:
                    group_widget = MixerGroupWidget(group, group_pairs, func_map)
                    tab_strips += group_widget.findChildren(ChannelStrip)
                    h.addWidget(group_widget)
            h.addStretch()
            strip.setLayout(h)
            scroll.setWidget(strip)
            tab_layout.addWidget(scroll, stretch=10)

            # Right: Output faders (never scrolls)
            out_L, out_R = f"Main-Out {pair[0]}", f"Main-Out {pair[1]}"
            output_widget = OutputFaderWidget(out_L, out_R)
            output_widget.setFixedWidth(260)
            tab_layout.addWidget(output_widget, stretch=0)
            self.tabs.addTab(tab, f"{pair[0]}/{pair[1]}")

            # Add output fader ChannelStrips
            tab_strips += output_widget.findChildren(ChannelStrip)
            # Save for this tab
            self.tab_channel_strips.append(tab_strips)

        # Add Patchbay tab
        patchbay_tab = PatchbayView(card_index=1)
        self.tabs.addTab(patchbay_tab, "Patchbay")
        # Patchbay has no faders for polling
        self.tab_channel_strips.append([])
        
        # Store reference to patchbay for bidirectional sync
        self.patchbay_view = patchbay_tab

        # --- Poll only the first tab's channels initially ---
        channel_names = [strip.channel_name for strip in self.tab_channel_strips[0]]
        self.alsa_worker = AlsaPollingWorker(channel_names, interval=0.5)
        self.alsa_worker.alsa_update.connect(self._alsa_update_received)

        # --- Switch polling when tab changes ---
        self.tabs.currentChanged.connect(self._tab_changed)

    def _tab_changed(self, index):
        # Change ALSA poller to watch the visible tab's strips only
        active_strips = self.tab_channel_strips[index]
        if active_strips:  # Regular mixer tab
            channel_names = [strip.channel_name for strip in active_strips]
            self.alsa_worker.set_channels(channel_names)
            self.active_strips = active_strips  # Save for updates
        else:
            # Patchbay tab - stop polling to avoid feedback loops
            self.alsa_worker.set_channels([])
            self.active_strips = []

    def _alsa_update_received(self, values):
        # Update the visible tab's strips
        for strip in getattr(self, "active_strips", self.tab_channel_strips[0]):
            val = values.get(strip.channel_name)
            if val is not None and val != strip.fader.slider.value():
                strip.fader.slider.blockSignals(True)
                strip.fader.slider.setValue(val)
                strip.fader.slider.blockSignals(False)
                strip.db_label.setText(f"{val}")
        
        # Update patchbay blocks for bidirectional sync (only when not on patchbay tab)
        if hasattr(self, 'patchbay_view') and self.tabs.currentIndex() != 4:  # Not on patchbay tab
            self._update_patchbay_from_alsa(values)

    def _update_patchbay_from_alsa(self, values):
        """Update patchbay blocks when ALSA values change from mixer tabs."""
        if not hasattr(self, 'patchbay_view'):
            return
            
        # Track which groups need updating
        groups_to_update = set()
        
        for item in self.patchbay_view.graphics_scene.items():
            # Update ChannelBlock objects
            if hasattr(item, 'ctl_name') and hasattr(item, 'update_fader') and hasattr(item, 'fader_value'):
                val = values.get(item.ctl_name)  # type: ignore
                if val is not None and val != item.fader_value:  # type: ignore
                    # Update without triggering ALSA write (skip_alsa=True)
                    item.fader_value = val  # type: ignore
                    item.update_fader(skip_alsa=True)  # type: ignore
                    item.value_text.setPlainText(str(val))  # type: ignore
                    
                    # If this block is part of a group, mark the group for updating
                    if hasattr(item, 'current_group') and item.current_group:  # type: ignore
                        groups_to_update.add(item.current_group)  # type: ignore
        
        # Update groups that contain updated blocks
        for group in groups_to_update:
            self._update_group_from_blocks(group)
    
    def _update_group_from_blocks(self, group):
        """Update group faders and displays based on underlying block values."""
        if not hasattr(group, 'block1') or not hasattr(group, 'block2'):
            return
            
        # Get current block values
        val1 = group.block1.fader_value  # type: ignore
        val2 = group.block2.fader_value  # type: ignore
        
        # Calculate macro fader level (average of both blocks)
        macro_level = (val1 + val2) // 2
        
        # Calculate crossfader position based on relative levels
        if val1 + val2 > 0:  # Avoid division by zero
            # Use inverse of the pan law to calculate crossfader position
            # This is an approximation - for exact calculation we'd need to solve the pan equation
            total = val1 + val2
            if total > 0:
                ratio = val1 / total
                # Convert ratio to crossfader position (0-100)
                # This is a simplified calculation - the exact math depends on the pan law used
                crossfader_pos = int(ratio * 100)
            else:
                crossfader_pos = 50
        else:
            crossfader_pos = 50
        
        # Update group faders without triggering signals
        group.macro_fader.blockSignals(True)
        group.crossfader.blockSignals(True)
        
        group.macro_fader.setValue(macro_level)
        group.crossfader.setValue(crossfader_pos)
        
        group.macro_fader.blockSignals(False)
        group.crossfader.blockSignals(False)
        
        # Update volume displays
        group.vol1_text.setPlainText(str(val1))
        group.vol2_text.setPlainText(str(val2))

