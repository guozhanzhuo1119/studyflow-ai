<template>
  <div class="md-viewer" v-html="rendered" />
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import katex from 'markdown-it-katex'
import hljs from 'highlight.js'
import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github.css'

const props = defineProps({
  source: { type: String, default: '' }
})

const md = new MarkdownIt({
  html: true,
  linkify: true,
  breaks: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
      } catch (_) {}
    }
    return ''
  }
})
md.use(katex)

const rendered = computed(() => {
  if (!props.source) return ''
  return md.render(props.source)
})
</script>

<style scoped>
.md-viewer {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  word-break: break-word;
}
.md-viewer :deep(img) {
  max-width: 100%;
  border-radius: 6px;
  margin: 8px 0;
  cursor: zoom-in;
}
.md-viewer :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
.md-viewer :deep(pre) {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
.md-viewer :deep(pre code) {
  background: transparent;
  padding: 0;
}
.md-viewer :deep(table) {
  border-collapse: collapse;
  margin: 10px 0;
  width: 100%;
}
.md-viewer :deep(th),
.md-viewer :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
}
.md-viewer :deep(blockquote) {
  border-left: 3px solid #409eff;
  margin: 10px 0;
  padding-left: 12px;
  color: #606266;
}
</style>
