
function cachedProperty(_: unknown, key: string, descriptor: PropertyDescriptor): PropertyDescriptor {
  const originalGetter = descriptor.get
  if (!originalGetter) {
    throw new Error('The decorated property must have a getter.')
  }

  // Use a Symbol for storing the cached value on the instance
  const cachedValueKey = Symbol(`__cached_${key}`)
  /* eslint-disable  @typescript-eslint/no-explicit-any */
  descriptor.get = function(this: any): any {
    if (!this[cachedValueKey]) {
      this[cachedValueKey] = originalGetter.call(this)
    }
    return this[cachedValueKey]
  }
  return descriptor
}

export default cachedProperty
