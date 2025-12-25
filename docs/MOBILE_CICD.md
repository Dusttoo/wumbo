# Mobile App CI/CD with EAS Build

This document outlines the CI/CD strategy for the Wumbo mobile app using Expo Application Services (EAS Build).

## Overview

The mobile app uses:
- **Expo SDK 54** with React Native 0.81.5
- **Expo Router 6** for navigation
- **EAS Build** for cloud-based builds
- **EAS Submit** for app store submissions
- **EAS Update** for over-the-air updates

## Prerequisites

1. **Expo Account**
   - Sign up at https://expo.dev
   - Create an organization for your project

2. **Install EAS CLI**
   ```bash
   npm install -g eas-cli
   ```

3. **Login to Expo**
   ```bash
   eas login
   ```

4. **Configure Project**
   ```bash
   cd apps/mobile
   eas build:configure
   ```

## EAS Configuration

### `eas.json` Configuration

Create `apps/mobile/eas.json`:

```json
{
  "cli": {
    "version": ">= 5.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "ios": {
        "simulator": true
      },
      "android": {
        "buildType": "apk"
      },
      "env": {
        "EXPO_PUBLIC_API_URL": "https://dev-api.wumbo.app"
      }
    },
    "preview": {
      "distribution": "internal",
      "ios": {
        "simulator": false
      },
      "android": {
        "buildType": "apk"
      },
      "env": {
        "EXPO_PUBLIC_API_URL": "https://staging-api.wumbo.app"
      }
    },
    "production": {
      "distribution": "store",
      "ios": {
        "simulator": false
      },
      "android": {
        "buildType": "aab"
      },
      "env": {
        "EXPO_PUBLIC_API_URL": "https://api.wumbo.app"
      }
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "your-apple-id@example.com",
        "ascAppId": "1234567890",
        "appleTeamId": "ABCDE12345"
      },
      "android": {
        "serviceAccountKeyPath": "./google-service-account.json",
        "track": "production"
      }
    }
  },
  "update": {
    "url": "https://u.expo.dev/your-project-id"
  }
}
```

## Build Profiles

### Development Build
- For internal testing and development
- Includes developer tools and debugging
- Can be installed on simulators/emulators

```bash
# iOS Simulator
eas build --profile development --platform ios

# Android APK
eas build --profile development --platform android
```

### Preview Build
- For beta testing
- Internal distribution (TestFlight, Google Play Internal Testing)
- Production-like environment

```bash
# iOS (TestFlight)
eas build --profile preview --platform ios

# Android (APK for testing)
eas build --profile preview --platform android
```

### Production Build
- For app store release
- Optimized and signed
- AAB for Android, IPA for iOS

```bash
# iOS App Store
eas build --profile production --platform ios

# Google Play Store
eas build --profile production --platform android
```

## App Store Setup

### iOS (App Store Connect)

1. **Create App in App Store Connect**
   - https://appstoreconnect.apple.com
   - Create new app with bundle ID: `com.familybudget.app`

2. **Create App Store Connect API Key**
   - App Store Connect > Users and Access > Keys
   - Generate new key with Developer role
   - Download and save securely

3. **Configure EAS**
   ```bash
   eas credentials
   ```

4. **Submit to TestFlight**
   ```bash
   eas submit --profile preview --platform ios
   ```

### Android (Google Play Console)

1. **Create App in Google Play Console**
   - https://play.google.com/console
   - Create new app

2. **Create Service Account**
   - Google Cloud Console
   - IAM & Admin > Service Accounts
   - Grant permissions for Play Store

3. **Download JSON Key**
   - Save as `google-service-account.json`
   - Add to `.gitignore`

4. **Submit to Internal Testing**
   ```bash
   eas submit --profile preview --platform android
   ```

## EAS Update (OTA Updates)

EAS Update allows you to push JavaScript and asset updates without going through app store review.

### Setup

1. **Configure Update URL**
   Already configured in `eas.json`

2. **Publish Update**
   ```bash
   # Development channel
   eas update --branch development --message "Fix login bug"

   # Production channel
   eas update --branch production --message "Update home screen"
   ```

3. **View Updates**
   ```bash
   eas update:list
   ```

## GitHub Actions Workflow

The mobile CI/CD workflow is defined in `.github/workflows/mobile-build.yml`:

### Workflow Triggers
- Push to `main` or `develop` branches (production/preview builds)
- Pull requests (run tests only)
- Manual dispatch (for on-demand builds)

### Build Process
1. Checkout code
2. Setup Node.js and dependencies
3. Run tests and linting
4. Authenticate with Expo
5. Build with EAS
6. Submit to app stores (production only)
7. Publish OTA update (if enabled)

## GitHub Secrets Configuration

Add these secrets to your GitHub repository:

1. **EXPO_TOKEN**
   - Generate: `eas whoami` > Profile > Access Tokens
   - Create token with build permissions

2. **APPLE_APP_STORE_CONNECT_API_KEY_ID**
3. **APPLE_APP_STORE_CONNECT_ISSUER_ID**
4. **APPLE_APP_STORE_CONNECT_API_KEY**
   - From App Store Connect API key creation

5. **GOOGLE_SERVICE_ACCOUNT_KEY**
   - Contents of `google-service-account.json`

## Local Testing

### Run on iOS Simulator
```bash
cd apps/mobile
npx expo start --ios
```

### Run on Android Emulator
```bash
cd apps/mobile
npx expo start --android
```

### Test Development Build
```bash
# Install development build on device
eas build --profile development --platform ios
# or
eas build --profile development --platform android

# Start development server
npx expo start --dev-client
```

## Best Practices

### Versioning
- Use semantic versioning (1.0.0, 1.1.0, etc.)
- Update `app.json` version and build number for each release
- iOS: `version` and `buildNumber`
- Android: `versionCode` and `versionName`

### Build Frequency
- **Development**: On-demand when testing new features
- **Preview**: Weekly or after significant features
- **Production**: Every 2-4 weeks or for critical fixes

### OTA Updates
- Use for minor bug fixes and UI tweaks
- Do NOT use for:
  - Native code changes
  - Dependency updates requiring rebuild
  - Critical security fixes (use full build)

### Testing
- Test preview builds on real devices before production
- Use TestFlight/Internal Testing for beta testing
- Get feedback from users before production release

## Troubleshooting

### Build Failures

**Issue**: Build fails with dependency errors
```bash
# Solution: Clear cache and reinstall
cd apps/mobile
rm -rf node_modules package-lock.json
npm install
eas build --clear-cache
```

**Issue**: iOS provisioning profile errors
```bash
# Solution: Regenerate credentials
eas credentials
# Select iOS > Select build profile > Regenerate
```

**Issue**: Android signing errors
```bash
# Solution: Regenerate keystore
eas credentials
# Select Android > Select build profile > Regenerate
```

### Submission Failures

**Issue**: App Store rejection
- Review App Store Review Guidelines
- Check for compliance issues
- Address feedback and resubmit

**Issue**: Google Play rejection
- Check Policy Center for violations
- Update app metadata and screenshots
- Resubmit with changes

## Cost Considerations

### EAS Build Pricing
- Free tier: Limited builds per month
- Priority tier: Unlimited builds with faster queues
- Production tier: Recommended for CI/CD

**Estimated Costs:**
- Free: $0/month (limited builds)
- Priority: $29/month (unlimited builds)
- Production: $99/month (faster builds, priority support)

### Optimization
- Use local builds for development testing
- Reserve EAS builds for preview/production
- Use OTA updates to reduce build frequency

## Resources

- [Expo EAS Build Documentation](https://docs.expo.dev/build/introduction/)
- [EAS Submit Documentation](https://docs.expo.dev/submit/introduction/)
- [EAS Update Documentation](https://docs.expo.dev/eas-update/introduction/)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Google Play Developer Policy](https://play.google.com/about/developer-content-policy/)
