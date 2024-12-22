# Static Directory

The `static` directory contains CSS files used for styling the Streamlit application, providing a consistent and visually appealing user interface.

## CSS Files

### `style.css`
- **Purpose**: Global styling for the entire application
- **Key Features**:
  - Imports the Geist font from Google Fonts
  - Sets default font properties for the application
  - Defines font styles for different elements
  - Ensures consistent typography across the app
- **Notable Configurations**:
  - Base font size: 16px
  - Primary font: Geist (with serif fallback)
  - Monospace font for code: Source Code Pro

### `advisors.css`
- **Purpose**: Specific styling for the advisors interface and chat components
- **Key Features**:
  - Customizes chat message styling
  - Adjusts avatar positioning and appearance
  - Defines styling for user and assistant messages
  - Configures input textarea and submit button
- **Notable Configurations**:
  - Custom chat message backgrounds
  - Responsive message width (5-80%)
  - Styled chat input with rounded corners
  - Hidden Streamlit deployment button
  - Custom color scheme for messages and inputs

## Usage

These CSS files are automatically loaded by Streamlit when the application starts. They provide a cohesive and modern design language for the application's user interface.

## Customization

To modify the application's appearance:
1. Edit the existing CSS files
2. Ensure changes maintain responsive design
3. Test across different screen sizes and devices