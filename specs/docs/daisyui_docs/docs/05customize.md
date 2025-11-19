自定义 daisyUI 组件
如何自定义 daisyUI？

daisyUI 组件自带了设计系统所需的多种变体，通常您不需要自定义任何东西。

但是，您仍然可以通过多种方式自定义组件。

比方说，您想自定义这个按钮：
<button class="btn">Button</button>
您可以使用 daisyUI 的工具类：
<button class="btn btn-primary">One</button>
<button class="btn btn-secondary">Two</button>
<button class="btn btn-accent btn-outline">Three</button>
  
您可以使用 Tailwind 的工具类：
<button class="btn rounded-full">One</button>
<button class="btn rounded-none px-16">Two</button>
 
您可以在 CSS 文件中，使用 Tailwind 的 @apply 指令来自定义组件：
@utility btn {
  @apply rounded-full;
}
