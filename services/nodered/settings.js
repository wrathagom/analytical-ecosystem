module.exports = {
    flowFile: 'flows.json',
    flowFilePretty: true,

    uiPort: process.env.PORT || 1880,

    adminAuth: {
        type: "credentials",
        users: [{
            username: process.env.NODERED_USER || "admin",
            password: process.env.NODERED_PASSWORD_HASH || "$2b$08$K3WmJkPM5RfDR7kuBvGn4eYKGlFmxLVdBNwMBwVH8GdNzDqLT0Wdm",
            permissions: "*"
        }]
    },

    functionGlobalContext: {},

    exportGlobalContextKeys: false,

    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },

    editorTheme: {
        projects: {
            enabled: false
        }
    }
};
