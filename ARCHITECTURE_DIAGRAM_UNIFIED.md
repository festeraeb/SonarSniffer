# Unified Rust Parser Architecture
## Visual Overview

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        sonar_gui.py                              │
│                    (User opens RSD file)                         │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  unified_rust_parser.py                          │
│                   (NEW - handles ALL formats)                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. detect_parser_type() → ParserType.RSD_GARMIN                │
│  2. UnifiedRustParser(file_path, gui_callback=log_status)       │
│  3. parser.parse_all()                                          │
│                                                                  │
└──────────┬──────────┬──────────────┬──────────────┬──────────────┘
           │          │              │              │
           ▼          ▼              ▼              ▼
    ┌────────────┐  ┌────────┐  ┌────────┐  ┌────────────────┐
    │ RSD (.rsd) │  │XTF(.xtf)  SLG(.slg) │  SDF(.sdf) │
    └─────┬──────┘  └────────┘  └────────┘  └────────────────┘
          │
          ▼
    ┌─────────────────────────────────┐
    │   Try Rust Acceleration         │
    │   (if available)                │
    │                                 │
    │ import rsd_parser_rust          │
    └─────┬───────────────────────────┘
          │
      ┌───┴────┐
      │        │
   SUCCESS   FAIL
      │        │
      │        ▼
      │   ┌──────────────────────────────┐
      │   │  Fall back to Python Parser  │
      │   │  (engine_classic_varstruct   │
      │   │   or engine_nextgen_syncfirst)
      │   └──────────┬───────────────────┘
      │              │
      └──────┬───────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Return Records List     │
    └──────────┬───────────────┘
               │
               ▼
    ┌──────────────────────────────────────┐
    │  Log to GUI:                         │
    │  ✓ Using: RSD (Garmin)               │
    │  ✓ [Rust Acceleration] or [Python]   │
    │  ✓ Processed X records in Y seconds  │
    └──────────────────────────────────────┘
```

---

## File Format Router

```
                    UNIFIED_RUST_PARSER
                           │
            ┌──────────────┬┼┬──────────────┐
            ▼              ▼ ▼              ▼
         RSD (Rust)    XTF  SLG    DAT  JSF  SDF
         + Fallback    (Py) (Py)   (Py) (Py) (Py)
            │
            ├─→ RSD Format?
            │   ├─→ Try: rsd_parser_rust (compiled Rust)
            │   └─→ Fallback: engine_classic_varstruct
            │
            └─→ Other Format?
                └─→ Direct to appropriate Python parser
                    (no Rust attempt yet)


LEGEND:
  Rust = Compiled Rust binary (fast)
  (Py) = Python parser (baseline)
```

---

## Class Hierarchy

```
┌─────────────────────────────────────────┐
│         unified_rust_parser.py          │
├─────────────────────────────────────────┤
│                                         │
│  • ParserType (Enum)                    │
│    ├─ RSD_GARMIN                        │
│    ├─ XTF_EDGETECH                      │
│    ├─ JSF_EDGETECH                      │
│    ├─ SLG_NAVICO                        │
│    ├─ SON_HUMMINBIRD                    │
│    ├─ DAT_HUMMINBIRD                    │
│    ├─ SDF_KLEIN                         │
│    └─ UNKNOWN                           │
│                                         │
│  • ParserStatus (Dataclass)             │
│    ├─ parser_type: ParserType           │
│    ├─ acceleration: str (Rust/Python)   │
│    ├─ rust_available: bool              │
│    ├─ fallback_reason: Optional[str]    │
│    ├─ attempt_count: int                │
│    └─ max_attempts: int                 │
│                                         │
│  • UnifiedRustParser (Main Class)       │
│    ├─ __init__(file_path, callback)    │
│    ├─ detect_parser_type()              │
│    ├─ _try_rust_parser()                │
│    ├─ _parse_with_python()              │
│    ├─ _parse_rsd_python()               │
│    ├─ _parse_xtf_python()               │
│    ├─ _parse_jsf_python()               │
│    ├─ _parse_multiformat_python()       │
│    ├─ parse_all()                       │
│    ├─ parse()                           │
│    ├─ get_parser_info()                 │
│    └─ _log_status(message)              │
│                                         │
│  • Helper Functions                     │
│    ├─ detect_parser_type(file_path)    │
│    ├─ _check_rust_available()           │
│    ├─ parse_sonar_file_unified()        │
│    └─ parse_sonar_file_iter()           │
│                                         │
└─────────────────────────────────────────┘
```

---

## GUI Integration Flow

```
sonar_gui.py - parse_file() method
│
├─ Line 1635: self.log_header("Parsing Records...")
├─ Line 1640: from unified_rust_parser import UnifiedRustParser
│
├─ Line 1645: def parser_status_callback(msg):
│             self.log_info(f"  Parser: {msg}")
│
├─ Line 1650: parser = UnifiedRustParser(
│             file_path, 
│             gui_callback=parser_status_callback
│             )
│
├─ Line 1655: records = parser.parse_all()
│
├─ Line 1660: parser_info = parser.get_parser_info()
│
├─ Line 1665: self.log_info(
│             f"Using: {parser_info['parser_type']} "
│             f"[{parser_info['acceleration']} Acceleration]"
│             )
│
└─ Line 1670: # Loop through records
              for record in records:
              record_count += 1
              # ... process record ...
              # Update progress every 5000 records
```

---

## Acceleration Decision Tree

```
START
│
├─→ Is file .RSD?
│   │
│   ├─YES→ Is Rust available?
│   │       │
│   │       ├─YES→ Try Rust parser
│   │       │       │
│   │       │       ├─SUCCESS→ Return Rust results ✓
│   │       │       │
│   │       │       └─FAIL→ Try Python fallback
│   │       │               └─ Return Python results ✓
│   │       │
│   │       └─NO→ Use Python parser
│   │               └─ Return Python results ✓
│   │
│   └─NO→ Is it XTF, SLG, SDF, etc?
│           │
│           ├─YES→ Use Python parser (ready for Rust)
│           │       └─ Return Python results ✓
│           │
│           └─NO→ UNKNOWN format
│                   └─ Raise error ✗
│
END
```

---

## State Machine: Parser Lifecycle

```
┌────────────────────┐
│   UnifiedRustParser │
│   Initialized      │
└────────────┬───────┘
             │
             ▼
      ┌──────────────┐
      │ Detect Type  │─────→ Sets: parser_type
      └──────┬───────┘       Sets: rust_available
             │
             ▼
      ┌──────────────┐
      │ Try Rust?    │
      │ (if RSD)     │
      └──────┬───────┘
             │
        ┌────┴────┐
        │         │
     SUCCESS    FAIL
        │         │
        ▼         ▼
    ┌────────┐ ┌──────────────────────┐
    │ Rust   │ │ Attempt Python?      │
    │ Ready  │ │ (always available)   │
    └────┬───┘ └──────────┬───────────┘
         │                │
         └────────┬───────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Return Records   │
         │ + Parser Info    │
         └──────┬───────────┘
                │
                ▼
         ┌──────────────────┐
         │ GUI Logs Status: │
         │ [Rust] or [Py]   │
         └──────────────────┘
```

---

## Performance Comparison (Expected)

```
FILE SIZE: 100 MB RSD

Scenario 1: Rust Built & Working
────────────────────────────────
Python Baseline:    ~8.5 seconds
Rust Accelerated:   ~0.85 seconds
───────────────────────────────
SPEEDUP:            10x faster ✓
GUI shows:          [Rust Acceleration]


Scenario 2: Rust Not Built
───────────────────────────
Attempted Rust:     FAIL (import error)
Fallback to Python: ~8.5 seconds
───────────────────────────────
SPEEDUP:            1x (baseline)
GUI shows:          [Python] (Fallback reason: Rust failed)


Scenario 3: XTF File
───────────────────
Python Parser:      ~4.2 seconds
Rust Support:       ⏳ Not yet
───────────────────────────────
Current:            1x (Python only)
GUI shows:          [Python]
Future:             Rust+Rust support → 15-30x
```

---

## Code Organization

```
rsd_parser_rust/  (compiled Rust library)
├── Cargo.toml
└── src/
    ├── lib.rs (PyO3 bindings)
    └── parsers/
        ├── mod.rs (module declarations)
        ├── garmin_rsd.rs (current: RSD parser)
        ├── edgetech_xtf.rs (future)
        ├── navico_slg.rs (future)
        └── klein_sdf.rs (future)

unified_rust_parser.py (Python integration layer)
├── ParserType (enum)
├── ParserStatus (dataclass)
├── UnifiedRustParser (main class)
│   ├── _try_rust_parser() → rsd_parser_rust
│   ├── _parse_rsd_python() → engine_classic_varstruct
│   ├── _parse_xtf_python() → robust_xtf_parser
│   └── _parse_*_python() → universal_sonar_parser
└── Helper functions

sonar_gui.py (GUI integration)
└── parse_file() method
    └── Creates UnifiedRustParser
    └── Calls parser.parse_all()
    └── Logs parser_info to GUI
```

---

## Timeline: From Click to Display

```
T=0ms   User clicks "Process File"
        ↓
T=10ms  GUI calls parse_file()
        ↓
T=15ms  Import unified_rust_parser module
        ↓
T=20ms  Create UnifiedRustParser(file_path)
        ├─ detect_parser_type() → RSD_GARMIN
        ├─ check Rust available → True
        └─ Initialize status
        ↓
T=25ms  Call parser.parse_all()
        ├─ Try Rust parser → SUCCESS
        └─ Return records list
        ↓
T=1000ms to 2000ms   (Actual parsing, Rust fast)
        ↓
T=2500ms  All records returned to GUI
        ├─ GUI logs "Using: RSD [Rust Acceleration]"
        ├─ GUI displays records count
        └─ GUI displays processing time
        ↓
T=2510ms  User sees results on screen
```

---

## Summary

✅ **Single Entry Point:** `UnifiedRustParser` handles all formats  
✅ **Auto-Detection:** File extension → parser type → implementation  
✅ **Transparent Fallback:** Try Rust, fall back to Python seamlessly  
✅ **User Visibility:** GUI logs which parser is active  
✅ **Zero-Risk:** Python always works, Rust is optional speedup  
✅ **Extensible:** New Rust optimizations auto-integrated  
✅ **Clean Code:** No format-specific branching in GUI  

**Status:** Ready for Phase 1 build and test 🚀
