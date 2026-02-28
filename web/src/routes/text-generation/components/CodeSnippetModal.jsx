import { Fragment, useContext, useState } from "react";
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  Tab,
  TabGroup,
  TabList,
  TabPanel,
  TabPanels,
  Transition,
  TransitionChild,
} from "@headlessui/react";
import {
  ClipboardDocumentIcon,
  CheckIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { ServiceContext } from "@/providers/ServiceProvider";
import PropTypes from "prop-types";
import { Highlight, themes } from "prism-react-renderer";
import Prism from "prismjs";

// Add languages not bundled by default
(typeof global !== "undefined" ? global : window).Prism = Prism;
import "prismjs/components/prism-bash";
import "prismjs/components/prism-r";

/**
 * Build a sample request body for the given mode and parameters.
 * @param {string} mode - "completion" or "chat"
 * @param {object} parameters - The API parameters
 * @returns {object} Sample request body
 */
function buildSampleBody(mode, parameters) {
  const body = { ...parameters, stream: false };

  if (mode === "completion") {
    body.prompt = "Your prompt here";
  } else {
    body.messages = [
      { role: "system", content: "You are a helpful assistant." },
      { role: "user", content: "Your message here" },
    ];
  }

  return body;
}

/**
 * Generate Python code for calling the service.
 * @param {string} mode - "completion" or "chat"
 * @param {object} parameters - The API parameters
 * @param {object} service - The selected service
 * @returns {string} Python code
 */
function generatePythonCode(mode, parameters, service) {
  const port = service?.port || 8000;
  const endpoint = mode === "completion" ? "v1/completions" : "v1/chat/completions";
  const body = buildSampleBody(mode, parameters);

  const bodyJson = JSON.stringify(body, null, 4)
    .split("\n")
    .map((line, i) => (i === 0 ? line : "    " + line))
    .join("\n");

  return `import requests

response = requests.post(
    "http://localhost:${port}/${endpoint}",
    json=${bodyJson}
)
print(response.json())`;
}

/**
 * Generate R code for calling the service.
 * @param {string} mode - "completion" or "chat"
 * @param {object} parameters - The API parameters
 * @param {object} service - The selected service
 * @returns {string} R code
 */
function generateRCode(mode, parameters, service) {
  const port = service?.port || 8000;
  const endpoint = mode === "completion" ? "v1/completions" : "v1/chat/completions";
  const body = buildSampleBody(mode, parameters);

  // Convert to R list syntax
  const formatRValue = (value, indent = 0) => {
    const spaces = "  ".repeat(indent);
    if (value === null) return "NULL";
    if (typeof value === "boolean") return value ? "TRUE" : "FALSE";
    if (typeof value === "number") return String(value);
    if (typeof value === "string") return `"${value.replace(/"/g, '\\"').replace(/\n/g, "\\n")}"`;
    if (Array.isArray(value)) {
      if (value.length === 0) return "list()";
      const items = value.map(v => formatRValue(v, indent + 1));
      return `list(\n${spaces}  ${items.join(`,\n${spaces}  `)}\n${spaces})`;
    }
    if (typeof value === "object") {
      const entries = Object.entries(value).map(([k, v]) => `${k} = ${formatRValue(v, indent + 1)}`);
      return `list(\n${spaces}  ${entries.join(`,\n${spaces}  `)}\n${spaces})`;
    }
    return String(value);
  };

  const bodyR = formatRValue(body, 1);

  return `library(httr)

response <- POST(
  "http://localhost:${port}/${endpoint}",
  body = ${bodyR},
  encode = "json"
)

content(response, "parsed")`;
}

/**
 * Generate Shell/curl code for calling the service.
 * @param {string} mode - "completion" or "chat"
 * @param {object} parameters - The API parameters
 * @param {object} service - The selected service
 * @returns {string} Shell code
 */
function generateShellCode(mode, parameters, service) {
  const port = service?.port || 8000;
  const endpoint = mode === "completion" ? "v1/completions" : "v1/chat/completions";
  const body = buildSampleBody(mode, parameters);

  const bodyJson = JSON.stringify(body, null, 2);
  // Escape single quotes for shell
  const escapedJson = bodyJson.replace(/'/g, "'\\''");

  return `curl -X POST "http://localhost:${port}/${endpoint}" \\
  -H "Content-Type: application/json" \\
  -d '${escapedJson}'`;
}

const languages = [
  { name: "Python", generate: generatePythonCode, prismLang: "python" },
  { name: "R", generate: generateRCode, prismLang: "r" },
  { name: "Shell", generate: generateShellCode, prismLang: "bash" },
];

/**
 * Code Snippet Modal component.
 * Shows generic API request examples for the selected service.
 * @param {object} options
 * @param {boolean} options.open - Whether the modal is open
 * @param {Function} options.onClose - Function to close the modal
 * @param {string} options.mode - "completion" or "chat"
 * @param {object} options.parameters - The API parameters
 * @return {JSX.Element}
 */
function CodeSnippetModal({
  open,
  onClose,
  mode,
  parameters,
}) {
  const serviceContext = useContext(ServiceContext);
  const selectedService = serviceContext?.selectedService;
  const [copied, setCopied] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const code = languages[selectedIndex].generate(mode, parameters, selectedService);

  const handleCopy = () => {
    navigator.clipboard
      .writeText(code)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch((err) => {
        console.error("Failed to copy code:", err);
      });
  };

  return (
    <Transition show={open} as={Fragment}>
      <Dialog as="div" className="relative z-[60]" onClose={onClose}>
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-80 transition-opacity" />
        </TransitionChild>

        <div className="fixed inset-0 z-10 w-screen overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <TransitionChild
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel className="relative transform rounded-lg bg-white dark:bg-gray-800 dark:ring-1 dark:ring-gray-700/50 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                  <DialogTitle
                    as="h3"
                    className="text-base font-semibold leading-6 text-gray-900 dark:text-gray-100"
                  >
                    API Code
                  </DialogTitle>
                  <button
                    type="button"
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="px-4 py-4">
                  <TabGroup selectedIndex={selectedIndex} onChange={setSelectedIndex}>
                    <TabList className="inline-flex space-x-1 rounded-md bg-gray-100 dark:bg-gray-700 p-0.5">
                      {languages.map((lang) => (
                        <Tab
                          key={lang.name}
                          className={({ selected }) =>
                            `rounded px-3 py-1 text-xs font-medium transition-colors
                            ${
                              selected
                                ? "bg-white dark:bg-gray-600 text-gray-900 dark:text-gray-100 shadow-sm"
                                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                            }`
                          }
                        >
                          {lang.name}
                        </Tab>
                      ))}
                    </TabList>
                    <TabPanels className="mt-3">
                      {languages.map((lang) => (
                        <TabPanel key={lang.name}>
                          <div className="relative group">
                            <button
                              type="button"
                              onClick={handleCopy}
                              className="absolute top-2 right-2 p-1.5 rounded-md text-gray-400 hover:text-gray-200 hover:bg-white/10 transition-colors z-10"
                              title="Copy code"
                            >
                              {copied ? (
                                <CheckIcon className="h-4 w-4 text-green-400" />
                              ) : (
                                <ClipboardDocumentIcon className="h-4 w-4" />
                              )}
                            </button>
                            <Highlight
                              theme={themes.vsDark}
                              code={lang.generate(mode, parameters, selectedService)}
                              language={lang.prismLang}
                            >
                              {({ style, tokens, getLineProps, getTokenProps }) => (
                                <pre
                                  style={style}
                                  className="rounded-lg p-4 max-h-96 overflow-auto text-xs font-mono"
                                >
                                  {tokens.map((line, i) => (
                                    <div key={i} {...getLineProps({ line })}>
                                      {line.map((token, key) => (
                                        <span key={key} {...getTokenProps({ token })} />
                                      ))}
                                    </div>
                                  ))}
                                </pre>
                              )}
                            </Highlight>
                          </div>
                        </TabPanel>
                      ))}
                    </TabPanels>
                  </TabGroup>
                </div>

              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

CodeSnippetModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  mode: PropTypes.oneOf(["completion", "chat"]).isRequired,
  parameters: PropTypes.object,
};

export default CodeSnippetModal;
