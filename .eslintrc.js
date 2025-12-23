module.exports = {
  root: true,
  extends: ['@family-budget/config/eslint/base'],
  ignorePatterns: [
    'node_modules/',
    'dist/',
    '.next/',
    '.expo/',
    'build/',
    'coverage/',
    '*.config.js',
  ],
};
