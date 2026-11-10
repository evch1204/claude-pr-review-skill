const express = require("express");
const session = require("./session");
const requireUser = require("./auth");
const accounts = require("./routes/accounts");

const app = express();
app.use(express.json());
app.use(session);
app.use(requireUser);
app.use(accounts);

module.exports = app;
