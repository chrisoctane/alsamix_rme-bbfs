from PyQt6.QtWidgets import QWidget, QTabWidget, QHBoxLayout, QVBoxLayout, QScrollArea, QTabBar
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import QRect, Qt, QSize
import alsa_backend
from mixer_channels import build_output_map, OUTPUT_TABS
from mixer_widgets import MixerGroupWidget, OutputFaderWidget, StereoPairStrip, ChannelStrip
from alsa_polling import AlsaPollingWorker
from patchbay_widget import PatchbayWidget
from mute_solo_manager import get_mute_solo_manager
from typing import cast
import re

class IndicatorTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_mute_present = []  # List of bools per tab
        self.tab_mute_active = []   # List of bools per tab
        self.tab_solo_present = []  # List of bools per tab
        self.tab_solo_active = []   # List of bools per tab

    def set_indicator_states(self, mute_present, mute_active, solo_present, solo_active):
        self.tab_mute_present = mute_present
        self.tab_mute_active = mute_active
        self.tab_solo_present = solo_present
        self.tab_solo_active = solo_active
        self.update()

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        # Add extra width for indicators and padding
        return size.expandedTo(QSize(120, size.height()))  # Minimum width 120px

    def paintEvent(self, event):
        painter = QPainter(self)
        font = painter.font()
        font.setBold(False)
        font.setPointSizeF(font.pointSizeF() * 0.9)  # Reduce font size by 10%
        painter.setFont(font)
        for i in range(self.count()):
            rect = self.tabRect(i)
            indicator_y = rect.center().y()
            mute_x = rect.left() + 8
            solo_x = rect.left() + 22
            # --- Highlight active tab ---
            if i == self.currentIndex():
                painter.save()
                highlight_color = QColor(255, 255, 180, 80)
                painter.setBrush(QBrush(highlight_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect)
                painter.restore()
            # --- Mute indicator (left) ---
            if i < len(self.tab_mute_present) and self.tab_mute_present[i]:
                if i < len(self.tab_mute_active) and self.tab_mute_active[i]:
                    painter.setPen(QPen(Qt.GlobalColor.black, 4))
                    painter.setBrush(QBrush(QColor("#f44336")))
                    painter.drawEllipse(mute_x, indicator_y-6, 12, 12)
                    painter.setPen(QPen(Qt.PenStyle.NoPen))
                    painter.setBrush(QBrush(QColor("#f44336")))
                    painter.drawEllipse(mute_x+3, indicator_y-3, 6, 6)
                else:
                    painter.setPen(QPen(Qt.GlobalColor.black, 2))
                    painter.setBrush(QBrush(QColor("#f44336")))
                    painter.drawEllipse(mute_x, indicator_y-6, 12, 12)
            else:
                painter.setPen(QPen(Qt.GlobalColor.black, 2))
                painter.setBrush(QBrush(QColor("#cccccc")))
                painter.drawEllipse(mute_x, indicator_y-6, 12, 12)
            # --- Solo indicator (right) ---
            if i < len(self.tab_solo_present) and self.tab_solo_present[i]:
                if i < len(self.tab_solo_active) and self.tab_solo_active[i]:
                    painter.setPen(QPen(Qt.GlobalColor.black, 4))
                    painter.setBrush(QBrush(QColor("#ffe066")))
                    painter.drawEllipse(solo_x, indicator_y-6, 12, 12)
                    painter.setPen(QPen(Qt.PenStyle.NoPen))
                    painter.setBrush(QBrush(QColor("#ffe066")))
                    painter.drawEllipse(solo_x+3, indicator_y-3, 6, 6)
                else:
                    painter.setPen(QPen(Qt.GlobalColor.black, 2))
                    painter.setBrush(QBrush(QColor("#ffe066")))
                    painter.drawEllipse(solo_x, indicator_y-6, 12, 12)
            else:
                painter.setPen(QPen(Qt.GlobalColor.black, 2))
                painter.setBrush(QBrush(QColor("#cccccc")))
                painter.drawEllipse(solo_x, indicator_y-6, 12, 12)
            # --- Draw tab text to the right of the indicators ---
            text_offset = solo_x + 16
            text_rect = QRect(text_offset, rect.top(), rect.width() - (text_offset - rect.left()) - 8, rect.height())
            tab_text = self.tabText(i)
            painter.setPen(QPen(QColor("#f8f8f8")))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, tab_text)

class OutputsTabs(QWidget):
    def __init__(self, card_index=1):
        super().__init__()
        self.tabs = QTabWidget()
        self.indicator_tabbar = IndicatorTabBar()
        self.tabs.setTabBar(self.indicator_tabbar)
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
            # Format tab name as 'PH 3/4' instead of 'PH3/PH4'
            def format_pair_name(a, b):
                import re
                m = re.match(r"([A-Za-z]+)[ -]?([0-9]+)", a)
                n = re.match(r"([A-Za-z]+)[ -]?([0-9]+)", b)
                if m and n and m.group(1) == n.group(1):
                    return f"{m.group(1)} {m.group(2)}/{n.group(2)}"
                return f"{a}/{b}"
            self.tabs.addTab(tab, format_pair_name(pair[0], pair[1]))

            # Add output fader ChannelStrips
            tab_strips += output_widget.findChildren(ChannelStrip)
            # Save for this tab
            self.tab_channel_strips.append(tab_strips)

        # Add Patchbay tab
        patchbay_widget = PatchbayWidget(card_index=1)
        self.tabs.addTab(patchbay_widget, "Patchbay")
        # Patchbay has no faders for polling
        self.tab_channel_strips.append([])
        
        # Store reference to patchbay for bidirectional sync
        self.patchbay_view = patchbay_widget.patchbay_view

        # --- Poll only the first tab's channels initially ---
        channel_names = [strip.channel_name for strip in self.tab_channel_strips[0]]
        self.alsa_worker = AlsaPollingWorker(channel_names, interval=0.5)
        self.alsa_worker.alsa_update.connect(self._alsa_update_received)

        # --- Switch polling when tab changes ---
        self.tabs.currentChanged.connect(self._tab_changed)
        
        # --- Initialize mute/solo manager and register UI callbacks ---
        self.mute_solo_manager = get_mute_solo_manager(card_index)
        self.mute_solo_manager.register_ui_callback(self._update_all_mute_solo_states)
        
        # Connect mute/solo signals
        self.mute_solo_manager.mute_state_changed.connect(self._on_mute_state_changed)
        self.mute_solo_manager.solo_state_changed.connect(self._on_solo_state_changed)
        self.mute_solo_manager.flash_state_changed.connect(self._on_flash_state_changed)
        
        # Track which tabs have soloed channels
        self.tab_solo_states = [False] * self.tabs.count()

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
            if val is not None and val != strip.fader.value():
                strip.fader.blockSignals(True)
                strip.fader.setValue(val)
                strip.fader.blockSignals(False)
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
    
    def _update_all_mute_solo_states(self):
        """Update mute/solo button states across all tabs."""
        for tab_strips in self.tab_channel_strips:
            for strip in tab_strips:
                if hasattr(strip, 'update_mute_solo_state'):
                    strip.update_mute_solo_state()
    
    def _on_mute_state_changed(self, channel_name: str, muted: bool):
        """Handle mute state changes from global manager."""
        # Update all channel strips for this channel across all tabs
        for tab_strips in self.tab_channel_strips:
            for strip in tab_strips:
                if strip.channel_name == channel_name and hasattr(strip, 'btn_mute'):
                    strip.btn_mute.setChecked(muted)
    
    def _on_solo_state_changed(self, channel_name: str, soloed: bool):
        """Handle solo state changes from global manager."""
        # Update all channel strips for this channel across all tabs
        for tab_strips in self.tab_channel_strips:
            for strip in tab_strips:
                if strip.channel_name == channel_name and hasattr(strip, 'btn_solo'):
                    strip.btn_solo.setChecked(soloed)
        
        # Update tab indicators
        self._update_tab_indicators()
    
    def _on_flash_state_changed(self, flash_on: bool):
        """Handle flash state changes from global manager."""
        # Update tab indicators based on flash state
        self._update_tab_indicators(flash_on)
    
    def _update_tab_indicators(self, flash_on: bool = False):
        """Update tab indicators: left (mute, red/grey), right (solo, yellow/grey). Custom drawing only. Uses explicit_mute/solo for active distinction."""
        mute_present = []
        mute_active = []
        solo_present = []
        solo_active = []
        for tab_strips in self.tab_channel_strips:
            has_mute_present = False
            has_mute_active = False
            has_solo_present = False
            has_solo_active = False
            for strip in tab_strips:
                if hasattr(strip, 'channel_name'):
                    state = self.mute_solo_manager.channel_states.get(strip.channel_name)
                    if state:
                        if state.muted:
                            has_mute_present = True
                        if state.explicit_mute:
                            has_mute_active = True
                        if state.soloed:
                            has_solo_present = True
                        if state.explicit_solo:
                            has_solo_active = True
            mute_present.append(has_mute_present)
            mute_active.append(has_mute_active)
            solo_present.append(has_solo_present)
            solo_active.append(has_solo_active)
        self.indicator_tabbar.set_indicator_states(mute_present, mute_active, solo_present, solo_active)

