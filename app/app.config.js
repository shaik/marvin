import 'dotenv/config';

export default {
  expo: {
    name: "Marvin",
    slug: "marvin-memory-assistant",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    splash: {
      image: "./assets/splash.png",
      resizeMode: "contain",
      backgroundColor: "#ffffff"
    },
    assetBundlePatterns: [
      "**/*"
    ],
    ios: {
      supportsTablet: true
    },
    android: {
      adaptiveIcon: {
        foregroundImage: "./assets/adaptive-icon.png",
        backgroundColor: "#ffffff"
      }
    },
    web: {
      favicon: "./assets/favicon.png"
    },
    extra: {
      HEROKU_URL: process.env.HEROKU_URL || "",
      API_AUTH_KEY: process.env.API_AUTH_KEY || ""
    }
  }
};