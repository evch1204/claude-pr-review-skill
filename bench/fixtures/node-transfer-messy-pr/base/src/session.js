// Cookie session middleware. Cookie is httpOnly + secure, sameSite=none
// (required so the embedded partner widget on other origins stays logged in).
// Details omitted.
module.exports = function session(req, _res, next) { next(); };
