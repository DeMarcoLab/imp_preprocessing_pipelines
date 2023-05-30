"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.tomosetRouter = void 0;
const express_1 = __importDefault(require("express"));
const mongodb_1 = require("mongodb");
const database_service_1 = require("../services/database.service");
exports.tomosetRouter = express_1.default.Router();
exports.tomosetRouter.use(express_1.default.json());
exports.tomosetRouter.get("/:user_id", (_req, res) => __awaiter(void 0, void 0, void 0, function* () {
    var _a;
    //only return datasets that are set to public or private to that user.
    const id = (_a = _req === null || _req === void 0 ? void 0 : _req.params) === null || _a === void 0 ? void 0 : _a.user_id;
    try {
        const tomosets = (yield database_service_1.collections.tomosets.find({ $or: [{ "access.privacy": "public" }, { "access.user": id }] }).toArray());
        res.status(200).send(tomosets);
    }
    catch (error) {
        res.status(500).send(error.message);
    }
}));
// Example route: http://localhost:8080/tomosets/610aaf458025d42e7ca9fcd0
exports.tomosetRouter.get("/getOne/:name", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    var _b;
    const name = (_b = req === null || req === void 0 ? void 0 : req.params) === null || _b === void 0 ? void 0 : _b.name;
    try {
        // _id in MongoDB is an objectID type so we need to find our specific document by querying
        const query = { name: name };
        const tomoset = (yield database_service_1.collections.tomosets.findOne(query));
        if (tomoset) {
            res.status(200).send(tomoset);
        }
    }
    catch (error) {
        res.status(404).send(`Unable to find matching document with name: ${req.params.name}`);
    }
}));
//special entry for statistics. it's in the same collection as all the other datasets - this is probably not great? Not sure what the implications are.
exports.tomosetRouter.get("/getStatisticsObject/", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const query = { name: "statObject" };
        const tomoset = (yield database_service_1.collections.tomosets.findOne(query));
        if (tomoset) {
            res.status(200).send(tomoset);
        }
    }
    catch (error) {
        res.status(404).send(`Unable to find matching statistics object`);
    }
}));
//updates the statistics object.
exports.tomosetRouter.post("/setStatisticsObject/", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const updatedStatisticsObject = req.body;
        const query = { name: "statObject" };
        const result = yield database_service_1.collections.tomosets.updateOne(query, { $set: updatedStatisticsObject });
        result
            ? res.status(200).send(`Successfully updated statObject `)
            : res.status(304).send(`Stat object not updated`);
    }
    catch (error) {
        if (error.response) {
            res.status(400).send(error.response);
        }
        else if (error.request) {
            //do something else
            res.status(400).send(error.request);
        }
        else if (error.message) {
            //do something other than the other two
            res.status(400).send(error.message);
        }
    }
}));
exports.tomosetRouter.post("/addDataset", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const newtomoset = req.body;
        const result = yield database_service_1.collections.tomosets.insertOne(newtomoset);
        result
            ? res.status(201).send(`Successfully created a new tomoset with id ${result.insertedId}`)
            : res.status(500).send("Failed to create a new tomoset.");
    }
    catch (error) {
        console.error(error);
        res.status(400).send(error.message);
    }
}));
exports.tomosetRouter.put("/:name", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    var _c;
    const datasetName = (_c = req === null || req === void 0 ? void 0 : req.params) === null || _c === void 0 ? void 0 : _c.name;
    try {
        const updatedtomoset = req.body;
        const query = { name: datasetName };
        // $set adds or updates all fields
        const result = yield database_service_1.collections.tomosets.updateOne(query, { $set: updatedtomoset });
        result
            ? res.status(200).send(`Successfully updated tomoset with name ${datasetName}`)
            : res.status(304).send(`tomoset with name: ${datasetName} not updated`);
    }
    catch (error) {
        if (error.response) {
            res.status(400).send(error.response);
        }
        else if (error.request) {
            //do something else
            res.status(400).send(error.request);
        }
        else if (error.message) {
            //do something other than the other two
            res.status(400).send(error.message);
        }
    }
}));
exports.tomosetRouter.delete("/:id", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    var _d;
    const id = (_d = req === null || req === void 0 ? void 0 : req.params) === null || _d === void 0 ? void 0 : _d.id;
    try {
        const query = { _id: new mongodb_1.ObjectId(id) };
        const result = yield database_service_1.collections.tomosets.deleteOne(query);
        if (result && result.deletedCount) {
            res.status(202).send(`Successfully removed tomoset with id ${id}`);
        }
        else if (!result) {
            res.status(400).send(`Failed to remove tomoset with id ${id}`);
        }
        else if (!result.deletedCount) {
            res.status(404).send(`tomoset with id ${id} does not exist`);
        }
    }
    catch (error) {
        console.error(error.message);
        res.status(400).send(error.message);
    }
}));
//# sourceMappingURL=tomoset.router.js.map