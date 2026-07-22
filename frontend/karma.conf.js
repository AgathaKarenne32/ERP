// Karma config pinned to a headless Chromium. In CI / containers set
// CHROME_BIN to the Chromium binary (this repo's dev env ships one at
// /opt/pw-browsers/chromium — see below).
process.env.CHROME_BIN =
  process.env.CHROME_BIN || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('@angular-devkit/build-angular/plugins/karma'),
    ],
    reporters: ['progress'],
    browsers: ['ChromeHeadlessNoSandbox'],
    customLaunchers: {
      ChromeHeadlessNoSandbox: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox', '--disable-gpu', '--headless=new'],
      },
    },
    restartOnFileChange: false,
    singleRun: true,
  });
};
