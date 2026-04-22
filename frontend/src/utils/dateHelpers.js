export function toOffsetIsoString(datetimeLocalValue) {
  const localDate = new Date(datetimeLocalValue);
  return localDate.toISOString();
}

export function toDateTimeLocalValue(date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 16);
}
