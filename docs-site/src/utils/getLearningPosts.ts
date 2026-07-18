import type { CollectionEntry } from "astro:content";
import postFilter from "./postFilter";

const getLearningPosts = (posts: CollectionEntry<"blog">[]) =>
  posts
    .filter(postFilter)
    .sort((a, b) => a.data.learningOrder - b.data.learningOrder);

export default getLearningPosts;
