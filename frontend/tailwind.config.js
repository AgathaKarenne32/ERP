/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        // Own palette, similar in spirit to a marketplace (yellow + blue accents)
        // without copying any brand's identity.
        brand: {
          yellow: '#ffe600',
          blue: '#2d3277',
          light: '#fff159',
        },
      },
    },
  },
  plugins: [],
};
