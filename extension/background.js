/**
 * Background service worker — required by Manifest V3.
 *
 * Currently minimal. Future enhancements:
 * - Periodic surveillance checks using chrome.alarms
 * - Desktop notifications for new job postings
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("Job Scrape Agent extension installed.");
});
