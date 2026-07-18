import { BLOG_PATH } from "@/content.config";
import { slugifyStr } from "./slugify";

/**
 * Get full path of a blog post
 * @param id - id of the blog post (aka slug)
 * @param filePath - the blog post full file location
 * @param includeBase - whether to include `/posts` in return value
 * @returns blog post path
 */
export function getPath(
  id: string,
  filePath: string | undefined,
  includeBase = true,
  includeBaseUrl = true
) {
  const pathSegments = filePath
    ?.replace(BLOG_PATH, "")
    .split("/")
    .filter(path => path !== "") // remove empty string in the segments ["", "other-path"] <- empty string will be removed
    .filter(path => !path.startsWith("_")) // exclude directories start with underscore "_"
    .slice(0, -1) // remove the last segment_ file name_ since it's unnecessary
    .map(segment => slugifyStr(segment)); // slugify each segment path

  const basePath = includeBase ? "/posts" : "";

  // Making sure `blogId` is slugified
  const blogId = id.split("/");
  const rawId = blogId.length > 0 ? blogId.slice(-1)[0] : id;
  const slug = slugifyStr(rawId);

  const path = !pathSegments || pathSegments.length < 1
    ? [basePath, slug].join("/")
    : [basePath, ...pathSegments, slug].join("/");

  if (!includeBaseUrl) return path.replace(/^\//, "");

  // Ensure double slashes are handled and BASE_URL is prepended
  const baseUrl = import.meta.env.BASE_URL.replace(/\/$/, "");
  return `${baseUrl}${path.startsWith("/") ? path : "/" + path}`;
}
