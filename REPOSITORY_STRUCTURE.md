# SonarSniffer Repository Structure

## Branch Organization

SonarSniffer uses a multi-branch strategy to separate commercial sonar analysis from SAR platform development.

### 🎣 **master** - SonarSniffer (Commercial Sonar Analysis)
- **Purpose**: Professional marine survey analysis tool
- **Core Features**: RSD, XTF, JSF, EdgeTech parsing; sonar visualization; geographic analysis
- **Licensing**: 30-day trial → commercial licenses
- **License Revenue**: Funds CesarOps SAR platform development
- **Users**: Fishing companies, marine researchers, boating enthusiasts

**Key Files:**
- `license_key_generator.py` - Generate trial/commercial license keys
- `license_validator.py` - Validate licenses at runtime
- `SONARSNIFFER_LICENSE_README.md` - Complete licensing documentation

---

### 🚁 **cesarops-platform** - CesarOps SAR Platform
- **Purpose**: Integrated Search & Rescue operations platform funded by SonarSniffer sales
- **Phase 1**: Community feedback survey (deadline: Dec 31, 2025)
- **Content**: SAR stakeholder survey, community input gathering
- **Target Users**: SAR teams, volunteers, emergency management, coastal communities

**Key Files:**
- `SAR_PLATFORM_SURVEY_INTERACTIVE.html` - Web form for survey submission
- `EMAIL_SURVEY_TEMPLATE.md` - Email distribution template
- `SAR_PLATFORM_SURVEY.md` - Detailed survey questions and methodology
- `SURVEY_DISTRIBUTION_README.md` - Survey deployment and distribution guide

---

### 🏷️ **beta-clean** - Legacy Branch
- **Status**: Historical/archived
- **Contains**: Earlier SAR platform work (Nov-Dec 2025)
- **Retention**: Kept for reference and rollback capability

---

### 🗂️ **master-archive-2025-12-04** - Original Master Backup
- **Status**: Archived backup of original SonarSniffer master branch
- **Created**: December 4, 2025
- **Purpose**: Preservation and rollback capability
- **Do Not Use**: For reference/historical purposes only

---

## File Organization

### Sonar Analysis (master)
```
├── license_key_generator.py       # Key generation tool
├── license_validator.py           # Runtime license validation
├── SONARSNIFFER_LICENSE_README.md # Licensing guide
├── src/                           # Source code
├── samples/                       # Sample sonar files
├── .gitignore                     # Git configuration
└── README.md                      # Main documentation
```

### SAR Platform (cesarops-platform)
```
├── SAR_PLATFORM_SURVEY_INTERACTIVE.html    # Survey form
├── SAR_PLATFORM_SURVEY.md                  # Survey documentation
├── EMAIL_SURVEY_TEMPLATE.md                # Email distribution
├── SURVEY_DISTRIBUTION_README.md           # Deployment guide
├── SAR_STAKEHOLDER_SURVEY.md              # Stakeholder feedback
├── GOOGLE_FORMS_TEMPLATE.md               # Alternative submission
├── sar_platform_core/                      # Platform backend
│   ├── intake_api.py              # API endpoints
│   ├── survey_handler.py          # Database operations
│   ├── models.py                  # Data models
│   └── sar_platform.db            # SQLite database
└── monitor_server.py              # Real-time monitoring
```

---

## Development Workflow

### SonarSniffer Development (master)
1. Create feature branch from `master`
2. Implement sonar analysis features
3. Test on Windows/macOS/Linux
4. Validate licensing system
5. Merge to `master`
6. Create release tag (e.g., `v1.1.0`)

### CesarOps Development (cesarops-platform)
1. Create feature branch from `cesarops-platform`
2. Implement SAR platform features
3. Reference SonarSniffer licensing (pulled from master)
4. Merge to `cesarops-platform`
5. Create CesarOps release tag (e.g., `cesarops-v0.1.0`)

---

## License & Revenue Model

```
┌──────────────────────────────────────────┐
│    SonarSniffer Purchase/Trial            │
│    (Sonar Analysis Tool)                  │
└─────────────────┬────────────────────────┘
                  │
                  ↓ License Revenue
                  │
┌──────────────────────────────────────────┐
│    CesarOps SAR Platform                  │
│    (Search & Rescue Operations)           │
│                                            │
│    ✓ Case Management                      │
│    ✓ Resource Coordination                │
│    ✓ Team Communication                   │
│    ✓ Real-time Response Tracking          │
└──────────────────────────────────────────┘
```

### Revenue Sharing
- **SonarSniffer**: Covers ongoing marine analysis features
- **CesarOps**: 100% of SonarSniffer commercial license revenue
- **Transparency**: Quarterly reports at https://cesarops.org/funding

---

## Survey Timeline (CesarOps Phase 1)

| Date | Event |
|------|-------|
| Nov 26, 2025 | Survey created and distributed |
| Dec 31, 2025 | **DEADLINE: Survey responses due (Midnight)** |
| Jan 1, 2026 | Data analysis & feedback synthesis |
| Jan 15, 2026 | Feature prioritization complete |
| Feb 1, 2026 | Phase 2 development begins |

**Current Survey Status**: ✅ Live and collecting responses  
**Responses Recorded**: 4+ (as of Dec 4, 2025)

---

## Accessing Branches

### Download/Clone SonarSniffer (master)
```bash
git clone https://github.com/festeraeb/SonarSniffer.git
cd SonarSniffer
# Automatically on master branch
python license_key_generator.py trial --customer "Your Team"
```

### Access CesarOps Platform (cesarops-platform)
```bash
git clone https://github.com/festeraeb/SonarSniffer.git
cd SonarSniffer
git checkout cesarops-platform
# Survey and CesarOps files now available
open SAR_PLATFORM_SURVEY_INTERACTIVE.html  # macOS
# or
start SAR_PLATFORM_SURVEY_INTERACTIVE.html  # Windows
```

### Legacy Branches (beta-clean, master-archive)
```bash
# View only (do not push changes)
git checkout beta-clean      # Historical SAR work
git checkout master-archive-2025-12-04  # Original backup
```

---

## Contributing

### SonarSniffer Features
- Fork from `master`
- Create feature branch: `feature/your-feature`
- Validate licensing system works
- Submit PR to `master`
- Add CHANGELOG entry

### CesarOps Platform
- Fork from `cesarops-platform`
- Create feature branch: `feature/sar-feature`
- Update survey if needed
- Submit PR to `cesarops-platform`
- Include SAR community testing results

---

## Support & Contact

**SonarSniffer Questions**
- Email: festeraeb@yahoo.com
- Subject: "SonarSniffer Support"
- Include: License key (first 5 chars), error message, OS version

**CesarOps Platform Questions**
- Email: festeraeb@yahoo.com
- Subject: "CesarOps SAR Platform Support"
- Include: Organization name, deployment location, requirements

**Survey Feedback**
- Email: festeraeb@yahoo.com
- Subject: "SAR Platform Survey Response"
- Include: Completed survey or specific feedback

---

## Repository Statistics

| Metric | Value |
|--------|-------|
| **Primary Branches** | 4 (master, cesarops-platform, beta-clean, archive) |
| **Remote Branches** | 4 pushed to GitHub |
| **License Files** | 2 (generator, validator) |
| **Survey Files** | 6 (interactive form, email template, distribution guides) |
| **Active Users** | SAR teams + marine analysis professionals |
| **Next Deadline** | Dec 31, 2025 (Survey responses) |

---

## Version Info

- **SonarSniffer**: v1.0.0-beta (commercial sonar analysis)
- **CesarOps Platform**: Phase 1 (community survey)
- **License System**: v1.0 (trial + commercial)
- **Repository**: Updated Dec 4, 2025

---

**Repository**: https://github.com/festeraeb/SonarSniffer  
**Organization**: CesarOps Search & Rescue  
**Maintained by**: festeraeb  
**Last Updated**: December 4, 2025
