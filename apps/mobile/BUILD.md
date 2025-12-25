# Wumbo Mobile App - Build Guide

Quick reference for building and deploying the Wumbo mobile app.

## Quick Start

```bash
# Install dependencies
make install

# Start development server
make start
```

## Build Commands

### Development Builds
Development builds include the expo-dev-client for faster development iteration.

```bash
# iOS development build (for simulator or device)
make dev-ios

# Android development build (APK)
make dev-android
```

**When to use:** During active development when you need to test on real devices with hot reload support.

### Preview Builds
Preview builds are for internal testing before going to production.

```bash
# iOS preview build
make preview-ios

# Android preview build (APK)
make preview-android
```

**When to use:** For beta testing with team members or stakeholders. These builds don't require TestFlight or Google Play enrollment.

### Production Builds
Production builds are optimized and ready for store submission.

```bash
# iOS production build
make prod-ios

# Android production build (AAB for Google Play)
make prod-android

# Build both platforms
make build-all
```

**When to use:** When you're ready to submit to the App Store or Google Play Store.

## Submitting to Stores

After building for production:

```bash
# Submit iOS to App Store
make submit-ios

# Submit Android to Google Play
make submit-android
```

## Utility Commands

```bash
# Run linter
make lint

# Run tests
make test

# Clean build artifacts
make clean

# Check build status
make status

# View latest build logs
make logs

# View all available commands
make help
```

## Build Profiles Explained

### Development
- **Purpose:** Fast iteration during development
- **Features:** expo-dev-client, hot reload, debugging tools
- **Distribution:** Internal (via simulator/device)
- **API URL:** https://dev-api.wumbo.app

### Preview
- **Purpose:** Internal testing and QA
- **Features:** Production-like build, no dev tools
- **Distribution:** Internal (via direct install)
- **API URL:** https://staging-api.wumbo.app

### Production
- **Purpose:** Store submission and public release
- **Features:** Fully optimized, code obfuscation
- **Distribution:** App Store / Google Play
- **API URL:** https://api.wumbo.app

## Environment-Specific API URLs

The app automatically connects to different API endpoints based on build profile:

| Profile | iOS Bundle ID | Android Package | API URL |
|---------|---------------|-----------------|---------|
| Development | com.built-by-dusty.wumbo | com.built_by_dusty.wumbo | dev-api.wumbo.app |
| Preview | com.built-by-dusty.wumbo | com.built_by_dusty.wumbo | staging-api.wumbo.app |
| Production | com.built-by-dusty.wumbo | com.built_by_dusty.wumbo | api.wumbo.app |

## Troubleshooting

### "expo-dev-client not installed"
```bash
make install
```

### "Bundle identifier already exists"
Check your Apple Developer account and update bundle ID in `app.json`.

### Build fails on EAS
```bash
make logs  # View detailed error logs
```

### Clean start after errors
```bash
make clean
make install
```

## First Time Setup

1. **Install EAS CLI globally:**
   ```bash
   npm install -g eas-cli
   ```

2. **Login to Expo:**
   ```bash
   eas login
   ```

3. **Configure project:**
   ```bash
   cd apps/mobile
   make install
   ```

4. **Create your first build:**
   ```bash
   make dev-ios  # or make dev-android
   ```

## Production Release Checklist

Before running `make prod-ios` or `make prod-android`:

- [ ] Update version in `app.json`
- [ ] Test preview build on multiple devices
- [ ] Run `make lint` and fix any issues
- [ ] Run `make test` and ensure all tests pass
- [ ] Update App Store/Play Store metadata
- [ ] Prepare release notes
- [ ] Verify API_URL is set to production
- [ ] Build with `make prod-ios` or `make prod-android`
- [ ] Submit with `make submit-ios` or `make submit-android`

## Resources

- [EAS Build Documentation](https://docs.expo.dev/build/introduction/)
- [EAS Submit Documentation](https://docs.expo.dev/submit/introduction/)
- [Wumbo Backend API](https://github.com/yourusername/wumbo)
