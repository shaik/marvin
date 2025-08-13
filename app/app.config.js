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
      image: undefined,
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
        foregroundImage: undefined,
        backgroundColor: "#ffffff"
      }
    },
    web: {
      favicon: undefined
    },
    extra: {
      HEROKU_URL: process.env.HEROKU_URL || "",
      API_AUTH_KEY: process.env.API_AUTH_KEY || ""
    }
  }
};