# 1) Remove the stale static config (it references missing images)
git rm -f app.json 2>/dev/null || rm -f app.json

# 2) Make sure we only use the dynamic config (app.config.js) and it doesn't
#    reference non-existent icons/splash. If it does, comment them out for now.

# 3) Align Expo-managed modules to the exact SDK 53 ranges
npx @expo/cli@latest install expo-av@~15.1.7 expo-constants@~17.1.7 \
  expo-linear-gradient@~14.1.5 expo-location@~18.1.6 expo-status-bar@~2.2.3 \
  react-native-safe-area-context@5.4.0

# 4) Quiet the metro/config-plugins warnings (dev-only)
npm i -D @expo/config-plugins@~10.1.1 metro@0.82.0 metro-config@0.82.0 metro-resolver@0.82.0

# 5) Clean caches and restart
rm -rf .expo .expo-shared
npx @expo/cli@latest start -c
