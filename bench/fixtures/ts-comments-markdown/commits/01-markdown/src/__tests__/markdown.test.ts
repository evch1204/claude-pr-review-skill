import { renderMarkdown } from "../markdown";

test("renders bold", () => {
  expect(renderMarkdown("**hi**")).toBe("<strong>hi</strong>");
});
