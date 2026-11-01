// commitlint 配置：强制 Conventional Commits。
// 由 .husky/commit-msg 在每次提交时校验，违反即拒绝提交。
// 对应 AGENTS.md §6：feat:/fix:/refactor:/test:/docs:/chore:
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
  },
};
