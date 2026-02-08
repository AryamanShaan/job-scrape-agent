/**
 * Content script — injected into every page the user visits.
 *
 * Its only job: when the popup asks for the page HTML, grab it and send it back.
 * This avoids CORS issues — the browser already rendered the page, so we just
 * read the DOM and hand it to the popup.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getPageHTML") {
    sendResponse({
      html: document.documentElement.outerHTML,
      url: window.location.href,
    });
  }
  // Return true to keep the message channel open for async responses
  return true;
});
