"use client";

import { Avatar, AvatarImage } from "@/components/ui/avatar";

import Crumb from "./crumb";
import Markdown from "@/components/markdown";
import { Post } from "@/types/post";
import moment from "moment";
import { Card } from "@/components/ui/card";

export default function BlogDetail({ post }: { post: Post }) {
  return (
    <section className="py-16">
      <div className="container">
        <Crumb post={post} />
        <div className="rounded-2xl bg-base-200 p-8 shadow-sm animate-in fade-in">
          <h1 className="mb-4 max-w-3xl text-2xl font-bold md:text-4xl">
            {post.title}
          </h1>
          <div className="flex items-center gap-3 text-sm md:text-base">
            {post.author_avatar_url && (
              <Avatar className="h-8 w-8 border">
                <AvatarImage src={post.author_avatar_url} alt={post.author_name} />
              </Avatar>
            )}
            <div>
              {post.author_name && (
                <span className="font-medium">{post.author_name}</span>
              )}
              <span className="ml-2 text-base-content/60">
                {post.created_at && moment(post.created_at).fromNow()}
              </span>
            </div>
          </div>
        </div>
        <div className="relative py-8 grid max-w-(--breakpoint-xl) gap-4 lg:mt-0 lg:grid lg:grid-cols-12 lg:gap-6">
          {post.content && (
            <Card
              className="order-2 lg:order-none lg:col-span-8 px-4 transition hover:shadow-md animate-in fade-in slide-in-from-bottom-2 duration-700 bg-background"
            >
              <Markdown content={post.content} />
            </Card>
          )}
          <div className="order-1 flex h-fit flex-col text-sm lg:sticky lg:top-8 lg:order-none lg:col-span-3 lg:col-start-10 lg:text-xs"></div>
        </div>
      </div>
    </section>
  );
}
