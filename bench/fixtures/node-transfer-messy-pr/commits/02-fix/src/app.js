const express = require("express");
const session = require("./session");
const requireUser = require("./auth");
const accounts = require("./routes/accounts");
const transfers = require("./routes/transfers");

const app = express();
app.use(express.json());
app.use(session);
app.use(requireUser);
app.use(accounts);
app.use(transfers);

module.exports = app;
