import express, { Request, Response } from "express";
import { ObjectId } from "mongodb";
import { collections } from "../services/database.service";
import Tomoset from "../models/tomoset";

export const tomosetRouter = express.Router();

tomosetRouter.use(express.json());

tomosetRouter.get("/:user_id", async (_req: Request, res: Response) => {
    //only return datasets that are set to public or private to that user.
    const id = _req?.params?.user_id
    try {
    
        const tomosets = (await collections.tomosets.find({ $or: [{ "access.privacy": "public" }, { "access.user": id }] }).toArray()) as Tomoset[];

        res.status(200).send(tomosets);
    } catch (error) {
        res.status(500).send(error.message);
    }
});


// Example route: http://localhost:8080/tomosets/610aaf458025d42e7ca9fcd0
tomosetRouter.get("/getOne/:name", async (req: Request, res: Response) => {
    const name = req?.params?.name;

    try {
        // _id in MongoDB is an objectID type so we need to find our specific document by querying
        const query = { name: name };
        const tomoset = (await collections.tomosets.findOne(query)) as Tomoset;

        if (tomoset) {
            res.status(200).send(tomoset);
        }
    } catch (error) {
        res.status(404).send(`Unable to find matching document with name: ${req.params.name}`);
    }
});


//special entry for statistics. it's in the same collection as all the other datasets - this is probably not great? Not sure what the implications are.
tomosetRouter.get("/getStatisticsObject/", async (req: Request, res: Response) => {

    try {
        const query = { name: "statObject" };
        const tomoset = (await collections.tomosets.findOne(query)) as Tomoset;

        if (tomoset) {
            res.status(200).send(tomoset);
        }
    } catch (error) {
        res.status(404).send(`Unable to find matching statistics object`);
    }
});

//updates the statistics object.
tomosetRouter.post("/setStatisticsObject/", async (req: Request, res: Response) => {

    try {
        const updatedStatisticsObject = req.body;
        const query = { name: "statObject" };
        const result = await collections.tomosets.updateOne(query, { $set: updatedStatisticsObject });
        result
            ? res.status(200).send(`Successfully updated statObject `)
            : res.status(304).send(`Stat object not updated`);
    } catch (error) {
        if (error.response) {

            res.status(400).send(error.response);

        } else if (error.request) {

            //do something else
            res.status(400).send(error.request);

        } else if (error.message) {

            //do something other than the other two
            res.status(400).send(error.message);
        }
    }
});

tomosetRouter.post("/addDataset", async (req: Request, res: Response) => {
    try {
        const newtomoset = req.body as Tomoset;
        const result = await collections.tomosets.insertOne(newtomoset);

        result
            ? res.status(201).send(`Successfully created a new tomoset with id ${result.insertedId}`)
            : res.status(500).send("Failed to create a new tomoset.");
    } catch (error) {
        console.error(error);
        res.status(400).send(error.message);
    }
});

tomosetRouter.put("/:name", async (req: Request, res: Response) => {
    const datasetName = req?.params?.name;

    try {
        const updatedtomoset: any = req.body as any;
        const query = { name: datasetName };
        // $set adds or updates all fields
        const result = await collections.tomosets.updateOne(query, { $set: updatedtomoset });

        result
            ? res.status(200).send(`Successfully updated tomoset with name ${datasetName}`)
            : res.status(304).send(`tomoset with name: ${datasetName} not updated`);
    } catch (error) {

        if (error.response) {

            res.status(400).send(error.response);

        } else if (error.request) {

            //do something else
            res.status(400).send(error.request);

        } else if (error.message) {

            //do something other than the other two
            res.status(400).send(error.message);
        }

    }
});

tomosetRouter.delete("/:id", async (req: Request, res: Response) => {
    const id = req?.params?.id;

    try {
        const query = { _id: new ObjectId(id) };
        const result = await collections.tomosets.deleteOne(query);

        if (result && result.deletedCount) {
            res.status(202).send(`Successfully removed tomoset with id ${id}`);
        } else if (!result) {
            res.status(400).send(`Failed to remove tomoset with id ${id}`);
        } else if (!result.deletedCount) {
            res.status(404).send(`tomoset with id ${id} does not exist`);
        }
    } catch (error) {
        console.error(error.message);
        res.status(400).send(error.message);
    }
});
