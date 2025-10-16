#!/usr/bin/env python3
"""Final verification of Studio GUI functionality"""

import studio_gui_engines_v3_14

if __name__ == "__main__":
    print("🚀 Launching Enhanced RSD Studio GUI...")
    print("Features:")
    print("  📁 File Processing Tab - Standard RSD parsing and preview")
    print("  🎯 Target Detection Tab - Advanced SAR and wreck hunting")
    print("  ℹ️ About Tab - Software information")
    print("\nTarget Detection Available:", studio_gui_engines_v3_14.TARGET_DETECTION_AVAILABLE)
    print("\nStarting GUI...")
    
    app = studio_gui_engines_v3_14.App()
    app.title("Enhanced RSD Studio v3.14 - Tabbed Interface")
    app.geometry("1200x800")
    
    print("✅ GUI launched successfully!")
    print("💡 Use Ctrl+C in terminal or close window to exit")
    
    app.mainloop()