# SonarSniffer License System

## Overview

SonarSniffer uses a flexible licensing model that funds the **CesarOps Search & Rescue Platform** development and operations.

- **Trial Licenses**: 30-day free trial for evaluation
- **Commercial Licenses**: Perpetual, Annual, or Monthly subscriptions
- **Revenue**: 100% of license fees fund SAR operations and technology

## Trial License

When you first install SonarSniffer, it runs in **trial mode** automatically. No key needed.

**Trial Features:**
- Full access to all sonar analysis tools
- All parsing formats (RSD, XTF, JSF, EdgeTech, Klein, etc.)
- 30 days from first run
- Conversion to commercial license during or after trial

## Commercial Licenses

Purchase a commercial license to continue using SonarSniffer after the trial period.

### License Types

| Type | Duration | Use Case |
|------|----------|----------|
| **PERPETUAL** | Forever | Commercial operations, permanent deployments |
| **ANNUAL** | 1 year | Seasonal teams, annual budget cycles |
| **MONTHLY** | 1 month | Testing, temporary operations |

### How to Purchase

Contact: **festeraeb@yahoo.com**
Subject: "SonarSniffer License Purchase"

Include:
- Organization/Team name
- Desired license type (PERPETUAL, ANNUAL, MONTHLY)
- Primary use (marine survey, SAR operations, research, etc.)
- Number of deployments

**License fees fund:**
- CesarOps SAR platform development
- Real-time sonar monitoring systems
- Community SAR team training and support
- Technology infrastructure and maintenance

## Installing a License Key

### Command Line

```bash
# Generate trial key (for testing)
python license_key_generator.py trial --customer "Team Name"

# Generate commercial key (for distribution)
python license_key_generator.py commercial --customer "Organization" --type PERPETUAL

# List all generated keys
python license_key_generator.py list

# Get info about a specific key
python license_key_generator.py info --key "SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX"
```

### In SonarSniffer Application

When you launch SonarSniffer:
1. Check license status automatically
2. If trial expired, prompt to install license key
3. Copy license key from email
4. Paste into license dialog
5. Application validates and saves license

### Key Format

All SonarSniffer license keys follow this format:

```
SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX
```

- Product ID: `SNIFFER`
- 4 segments: 5 alphanumeric characters each
- Example: `SNIFFER-A1B2C-D3E4F-G5H6I-J7K8L`

## License Storage

License information is stored locally:

- **Windows**: `%USERPROFILE%\.sonarsniffer\license.json`
- **macOS/Linux**: `~/.sonarsniffer/license.json`

This file contains:
- License key
- License type (TRIAL or COMMERCIAL)
- Installation date
- Expiration date (if applicable)

You can safely copy this file to transfer your license to another machine.

## License Validation

The validator checks:

1. **Format Validation**: Key follows `SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX` pattern
2. **Trial Expiration**: Automatically enforced 30 days from first run
3. **Commercial Expiration**: Checks subscription status (if applicable)
4. **Key Database**: Validates against generated keys locally

## Expired Trial - What to Do

When your 30-day trial expires:

1. You'll see a message: "Trial license expired on YYYY-MM-DD"
2. SonarSniffer will not launch until a commercial license is installed
3. Email **festeraeb@yahoo.com** to purchase a license
4. Once purchased, you'll receive a commercial license key
5. Paste the key into the license dialog on next launch

## Subscription Renewal

For ANNUAL and MONTHLY licenses:

- 30 days before expiration: You'll receive a renewal reminder
- After expiration: SonarSniffer will prompt you to renew
- To renew: Contact support with your existing license key
- Renewal discount: 20% off for continued customers

## License Troubleshooting

### "Invalid license key format"
- Ensure you copied the entire key correctly
- Key should be: `SNIFFER-XXXXX-XXXXX-XXXXX-XXXXX`
- Check for extra spaces or characters

### "License file corrupted"
- Delete `~/.sonarsniffer/license.json`
- Restart SonarSniffer
- Re-enter your license key

### "Can't find license file"
- `.sonarsniffer` folder will be created automatically
- Ensure your user profile directory is accessible
- Check folder permissions

### "License expired but I just purchased"
- Allow up to 1 hour for license activation
- Restart SonarSniffer after license installation
- Contact support if issue persists

## Technical Details

### License Key Generation

Keys are generated using:
- Product ID: `SNIFFER`
- Customer name
- Timestamp information
- Cryptographic hashing (SHA-256)

Each key is unique and non-transferable (in commercial deployments).

### Trial Tracking

Trial expiration is calculated:
- **Installation Date**: Recorded when license first installed
- **Expiration**: Installation Date + 30 days
- **Enforcement**: Real-time comparison of system date vs. expiration date

### Key Validation Process

1. Format check (pattern matching)
2. Product ID verification (`SNIFFER`)
3. Segment validation (5 chars each)
4. Optional: Server-side validation (for commercial keys)

## FAQ

**Q: Can I use one license key on multiple machines?**
- Trial keys: Yes, unlimited machines
- Commercial keys: Single-machine enforcement (contact support for multi-machine licensing)

**Q: What if I reinstall Windows/macOS?**
- Copy your `~/.sonarsniffer/license.json` to new machine
- Or contact support for license key reactivation

**Q: Can I get a refund?**
- Contact support within 14 days of purchase
- 100% refund minus processing fees

**Q: How are my license fees used?**
- 100% fund CesarOps SAR operations
- Transparent reporting at: https://cesarops.org/funding
- Breakdown by quarter available on request

**Q: Is my license tied to my email address?**
- No, license is tied to the machine it's installed on
- You can transfer it by copying the license.json file
- Email serves only for purchase/support communication

## Support

For license-related questions or issues:

**Email**: festeraeb@yahoo.com  
**Subject**: "SonarSniffer License Support"  

Include:
- License key (or first 5 characters)
- Error message (if any)
- Your operating system and SonarSniffer version

---

**SonarSniffer Licensing**  
_Supporting marine survey analysis and SAR operations worldwide._

Thank you for supporting CesarOps Search & Rescue platform development!
