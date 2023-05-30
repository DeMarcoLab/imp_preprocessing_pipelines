import express from "express";

import { connectToDatabase } from "./services/database.service";
import { tomosetRouter } from "./routes/tomoset.router";

const app = express();
const port = 8085; // default port to listen

var cors = require('cors')


connectToDatabase()
    .then(() => {
        const bodyParser = require('body-parser');
        app.use(cors());
        app.options('*', cors());
        app.use(bodyParser.json({ limit: '2mb' }));
        app.use(bodyParser.urlencoded({ extended: true, limit: '2mb' }));
        // send all calls to /tomosets to our gamesRouter
        app.use("/tomosets", tomosetRouter);

        // start the Express server
        app.listen(port, () => {
            console.log(`Server started at http://localhost:${port}`);
        });
    })
    .catch((error: Error) => {
        console.error("Database connection failed", error);
        process.exit();
    });
