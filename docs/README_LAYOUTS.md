# Patchbay Layout Management

The patchbay now supports saving and loading layouts for different session configurations.

## Features

- **Save Layout**: Save current patchbay arrangement with name and description
- **Load Layout**: Restore previously saved layouts
- **Layout Management**: List, delete, and manage saved layouts
- **JSON Storage**: Layouts saved as JSON files in `layouts/` directory

## How to Use

1. Open the mixer and go to the "Patchbay" tab
2. Arrange blocks and groups as desired
3. Click "Save Layout" or "Load Layout" buttons in the toolbar
4. Use the dialog to manage your layouts

## File Format

Layouts are stored as JSON with block positions, fader values, groups, and states.

## File Storage

Layouts are stored as JSON files in the `layouts/` directory:
- Each layout is saved as `