import React from "react";
import { ClipboardDocumentIcon, CheckIcon } from "@heroicons/react/24/outline";
import PropTypes from "prop-types";

/**
 * Generate a random API key.
 *
 * Uses the Web Crypto API, which every browser Blackfish supports provides
 * over both HTTP and HTTPS. 32 hex characters (128 bits) is well past what a
 * service on a cluster network needs.
 * @return {string}
 */
export function generateApiKey() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * API key field for the service launcher.
 *
 * Pre-filled with a generated key so the safe choice is the default one: a
 * user who does not think about the service's network exposure still gets an
 * authenticated service. The key is shown rather than masked, and copyable,
 * because launch is the one moment the user has it — afterwards only a hint is
 * available, and recovering the value means reading the job script.
 * @param {object} options
 * @param {string} options.value
 * @param {Function} options.setValue
 * @param {boolean} options.disabled
 * @return {JSX.Element}
 */
function ServiceModalApiKeyInput({ value, setValue, disabled }) {
  const [copied, setCopied] = React.useState(false);
  const timeoutRef = React.useRef(null);

  React.useEffect(() => {
    return () => clearTimeout(timeoutRef.current);
  }, []);

  const handleCopy = () => {
    navigator.clipboard
      .writeText(value)
      .then(() => {
        setCopied(true);
        clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => setCopied(false), 2000);
      })
      .catch((err) => {
        console.error("Failed to copy API key:", err);
      });
  };

  return (
    <div>
      <label
        htmlFor="service-modal-api-key"
        className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100"
      >
        API Key
      </label>
      <div className="relative mt-2 rounded-md shadow-sm">
        <input
          id="service-modal-api-key"
          type="text"
          disabled={disabled}
          className="block w-full rounded-md border-0 py-1.5 pr-10 ring-inset focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:ring-1 disabled:ring-gray-300 dark:disabled:ring-gray-600 ring-1 ring-gray-300 dark:ring-gray-600 focus:ring-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        {value && (
          <button
            type="button"
            onClick={handleCopy}
            disabled={disabled}
            aria-label={copied ? "API key copied" : "Copy API key"}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:cursor-not-allowed"
          >
            {copied ? (
              <CheckIcon className="h-5 w-5 text-green-600" aria-hidden="true" />
            ) : (
              <ClipboardDocumentIcon className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        )}
      </div>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
        Copy this key — you will not be able to read it back from Blackfish
        later. Replace it with your own if you prefer, or clear it to leave the
        service open to anyone who can reach it.
      </p>
    </div>
  );
}

ServiceModalApiKeyInput.propTypes = {
  value: PropTypes.string,
  setValue: PropTypes.func,
  disabled: PropTypes.bool,
};

export default ServiceModalApiKeyInput;
