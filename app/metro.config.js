const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Add support for .env files
config.resolver.sourceExts.push('env');

module.exports = config;