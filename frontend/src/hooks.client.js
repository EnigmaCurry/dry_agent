// Globally intercept 401 unauthenticated errors and refresh the page
// to go to login form.
const originalFetch = window.fetch;
window.fetch = async (input, init) => {
  const response = await originalFetch(input, init);
  if (response.status === 401) {
    location.reload();
  }
  return response;
};
