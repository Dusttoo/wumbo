module.exports = {
  extends: ['@wumbo/config/eslint/base'],
  env: {
    'react-native/react-native': true,
  },
  plugins: ['react', 'react-native'],
  rules: {
    'react/react-in-jsx-scope': 'off', // Not needed with React 17+
    'react-native/no-unused-styles': 'warn',
    'react-native/no-inline-styles': 'warn',
  },
};
