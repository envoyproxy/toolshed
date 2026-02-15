module.exports = (path, options) => {
  // Call the defaultResolver to mimic the default behavior
  return options.defaultResolver(path, {
    ...options,
    packageFilter: (pkg) => {
      // If the package is an ESM package, modify it to work with Jest
      if (pkg.type === 'module') {
        // Force Jest to use the main entry point for ESM packages
        if (pkg.exports && pkg.exports['.']) {
          const exports = pkg.exports['.'];
          if (exports.import) {
            pkg.main = exports.import;
          } else if (typeof exports === 'string') {
            pkg.main = exports;
          }
        }
        // Remove the ESM type to treat it as CommonJS
        delete pkg.type;
      }
      return pkg;
    },
  });
};
