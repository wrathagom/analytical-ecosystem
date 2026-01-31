const DEFAULT_PASSWORD_HASH = "$2b$08$K3WmJkPM5RfDR7kuBvGn4eYKGlFmxLVdBNwMBwVH8GdNzDqLT0Wdm";

let passwordHash = DEFAULT_PASSWORD_HASH;
const rawHash = process.env.NODERED_PASSWORD_HASH;
if (rawHash) {
    passwordHash = rawHash;
} else if (process.env.NODERED_PASSWORD) {
    try {
        const bcrypt = require("bcryptjs");
        passwordHash = bcrypt.hashSync(process.env.NODERED_PASSWORD, 8);
    } catch (err) {
        console.warn("bcryptjs not available; falling back to default Node-RED password hash.");
    }
}

module.exports = {
    flowFile: 'flows.json',
    flowFilePretty: true,

    uiPort: process.env.PORT || 1880,

    adminAuth: {
        type: "credentials",
        users: [{
            username: process.env.NODERED_USER || "admin",
            password: passwordHash,
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
