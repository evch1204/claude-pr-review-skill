/** Populates req.user from the session cookie; 401s if not logged in. */
module.exports = function requireUser(req, res, next) {
  if (!req.session || !req.session.userId) return res.status(401).json({ error: "unauthorized" });
  req.user = { id: req.session.userId };
  next();
};
