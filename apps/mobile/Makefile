# Wumbo Mobile App - Build Commands
# ====================================
# Convenient commands for building and managing the mobile app

.PHONY: help install clean lint test
.PHONY: dev-ios dev-android
.PHONY: preview-ios preview-android
.PHONY: prod-ios prod-android
.PHONY: build-all prebuild start

# Default target
help:
	@echo "Wumbo Mobile App - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make install         - Install dependencies"
	@echo "  make start           - Start Expo dev server"
	@echo "  make prebuild        - Generate native projects"
	@echo "  make clean           - Clean build artifacts"
	@echo ""
	@echo "Development Builds (with expo-dev-client):"
	@echo "  make dev-ios         - Build iOS development client"
	@echo "  make dev-android     - Build Android development APK"
	@echo ""
	@echo "Preview Builds (internal testing):"
	@echo "  make preview-ios     - Build iOS preview build"
	@echo "  make preview-android - Build Android preview APK"
	@echo ""
	@echo "Production Builds (store submission):"
	@echo "  make prod-ios        - Build iOS production build"
	@echo "  make prod-android    - Build Android app bundle"
	@echo ""
	@echo "Build All:"
	@echo "  make build-all       - Build all platforms for production"
	@echo ""
	@echo "Quality & Testing:"
	@echo "  make lint            - Run linter"
	@echo "  make test            - Run tests"
	@echo ""

# Setup & Dependencies
install:
	@echo "📦 Installing dependencies..."
	npm install

start:
	@echo "🚀 Starting Expo dev server..."
	npx expo start

prebuild:
	@echo "🔨 Generating native projects..."
	npx expo prebuild --clean

# Development Builds (with expo-dev-client)
dev-ios:
	@echo "🍎 Building iOS development client..."
	@echo "This will create a build you can install on a physical device or simulator"
	eas build --profile development --platform ios

dev-android:
	@echo "🤖 Building Android development APK..."
	@echo "This will create a debug APK you can install on a device or emulator"
	eas build --profile development --platform android

# Preview Builds (for internal testing)
preview-ios:
	@echo "🍎 Building iOS preview build..."
	@echo "This is for internal testing before production"
	eas build --profile preview --platform ios

preview-android:
	@echo "🤖 Building Android preview APK..."
	@echo "This is for internal testing before production"
	eas build --profile preview --platform android

# Production Builds (for store submission)
prod-ios:
	@echo "🍎 Building iOS production build..."
	@echo "⚠️  This will be submitted to the App Store"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		eas build --profile production --platform ios; \
	else \
		echo "Build cancelled."; \
	fi

prod-android:
	@echo "🤖 Building Android production app bundle..."
	@echo "⚠️  This will be submitted to Google Play Store"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		eas build --profile production --platform android; \
	else \
		echo "Build cancelled."; \
	fi

# Build all platforms for production
build-all:
	@echo "🚀 Building all platforms for production..."
	@echo "⚠️  This will create production builds for both iOS and Android"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		eas build --profile production --platform all; \
	else \
		echo "Build cancelled."; \
	fi

# Quality & Testing
lint:
	@echo "🔍 Running linter..."
	npm run lint

test:
	@echo "🧪 Running tests..."
	npm test

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf node_modules
	rm -rf .expo
	rm -rf ios/build
	rm -rf android/build
	rm -rf android/.gradle
	@echo "✅ Clean complete! Run 'make install' to reinstall dependencies"

# Submit builds to stores
submit-ios:
	@echo "📱 Submitting iOS build to App Store..."
	eas submit --platform ios --latest

submit-android:
	@echo "📱 Submitting Android build to Google Play..."
	eas submit --platform android --latest

# Update app configuration
update-config:
	@echo "⚙️  Updating app configuration..."
	npx expo prebuild --clean

# Check EAS build status
status:
	@echo "📊 Checking EAS build status..."
	eas build:list

# View build logs
logs:
	@echo "📝 Viewing latest build logs..."
	eas build:view --latest
