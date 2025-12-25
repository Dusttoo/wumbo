module.exports = {
  root: true,
  extends: ['@wumbo/config/eslint/base'],
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
