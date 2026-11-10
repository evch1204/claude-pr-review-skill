/** Double-submit CSRF check. Required on every state-changing route (see CONTRIBUTING.md). */
module.exports = function csrfProtection(req, res, next) {
  const header = req.get("x-csrf-token");
  if (!header || header !== req.session.csrfToken) return res.status(403).json({ error: "bad csrf token" });
  next();
};
