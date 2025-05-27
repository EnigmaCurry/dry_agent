/**
 * Debounce a function by a delay
 * @param {Function} func
 * @param {number} delay
 * @returns {Function}
 */
export const debounce = (func, delay) => {
  let timer;
  return function () {
	const context = this;
	const args = arguments;
	clearTimeout(timer);
	timer = setTimeout(() => func.apply(context, args), delay);
  };
};

export function toTitleCase(str) {
  return str
    .toLowerCase()
    .split(" ")
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
