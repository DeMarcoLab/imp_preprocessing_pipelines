"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const database_service_1 = require("./services/database.service");
const tomoset_router_1 = require("./routes/tomoset.router");
const app = express_1.default();
const port = 8085; // default port to listen
var cors = require('cors');
database_service_1.connectToDatabase()
    .then(() => {
    const bodyParser = require('body-parser');
    app.use(cors());
    app.options('*', cors());
    app.use(bodyParser.json({ limit: '2mb' }));
    app.use(bodyParser.urlencoded({ extended: true, limit: '2mb' }));
    // send all calls to /tomosets to our gamesRouter
    app.use("/tomosets", tomoset_router_1.tomosetRouter);
    // start the Express server
    app.listen(port, () => {
        console.log(`Server started at http://localhost:${port}`);
    });
})
    .catch((error) => {
    console.error("Database connection failed", error);
    process.exit();
});
//# sourceMappingURL=index.js.map