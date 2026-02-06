import { Fragment, useContext, useState, useEffect, useRef } from "react";
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
import Prism from "prismjs";
import "prismjs/components/prism-python";
import "prismjs/components/prism-r";
import "prismjs/components/prism-bash";
import "prismjs/themes/prism-tomorrow.css";

/**
 * Generate Python code for calling the service.
 * @param {string} mode - "completion" or "chat"
 * @param {string} prompt - The prompt text (for completion mode)
 * @param {Array} messages - The messages array (for chat mode)
 * @param {object} systemMessage - The system message (for chat mode)
 * @param {object} parameters - The API parameters
 * @param {object} service - The selected service
 * @returns {string} Python code
 */
function generatePythonCode(mode, prompt, messages, systemMessage, parameters, service) {
  const port = service?.port || 8000;
  const endpoint = mode === "completion" ? "v1/completions" : "v1/chat/completions";

  // Build the request body
  const body = { ...parameters, stream: false };

  if (mode === "completion") {
    body.prompt = prompt || "";
  } else {
    const allMessages = [];
    if (systemMessage?.content) {
      allMessages.push({ role: "system", content: systemMessage.content });
    }
    allMessages.push(...messages);
    body.messages = allMessages;
  }

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
 * @param {string} prompt - The prompt text (for completion mode)
 * @param {Array} messages - The messages array (for chat mode)
 * @param {object} systemMessage - The system message (for chat mode)
 * @param {object} parameters - The API parameters
 * @param {object} service - The selected service
 * @returns {string} R code
 */
function generateRCode(mode, prompt, messages, systemMessage, parameters, service) {
  const port = service?.port || 8000;
  const endpoint = mode === "completion" ? "v1/completions" : "v1/chat/completions";

  // Build the request body
  const body = { ...parameters, stream: false };

  if (mode === "completion") {
    body.prompt = prompt || "";
  } else {
    const allMessages = [];
    if (systemMessage?.content) {
      allMessages.push({ role: "system", content: systemMessage.content });
    }
    allMessages.push(...messages);
    body.messages = allMessages;
  }

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
 * @param {string} prompt - The prompt text (for completion mode)
 * @param {Array} messages - The messages array (for chat mode)
 * @param {object} systemMessage - The system message (for chat mode)
 * @param {object} parameters - The API parameters
 * @param {object} service - The selected service
 * @returns {string} Shell code
 */
function generateShellCode(mode, prompt, messages, systemMessage, parameters, service) {
  const port = service?.port || 8000;
  const endpoint = mode === "completion" ? "v1/completions" : "v1/chat/completions";

  // Build the request body
  const body = { ...parameters, stream: false };

  if (mode === "completion") {
    body.prompt = prompt || "";
  } else {
    const allMessages = [];
    if (systemMessage?.content) {
      allMessages.push({ role: "system", content: systemMessage.content });
    }
    allMessages.push(...messages);
    body.messages = allMessages;
  }

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
 * @param {object} options
 * @param {boolean} options.open - Whether the modal is open
 * @param {Function} options.onClose - Function to close the modal
 * @param {string} options.mode - "completion" or "chat"
 * @param {string} options.prompt - The prompt text (for completion mode)
 * @param {Array} options.messages - The messages array (for chat mode)
 * @param {object} options.systemMessage - The system message (for chat mode)
 * @param {object} options.parameters - The API parameters
 * @return {JSX.Element}
 */
function CodeSnippetModal({
  open,
  onClose,
  mode,
  prompt,
  messages,
  systemMessage,
  parameters,
}) {
  const serviceContext = useContext(ServiceContext);
  const selectedService = serviceContext?.selectedService;
  const [copied, setCopied] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const codeRef = useRef(null);

  const code = languages[selectedIndex].generate(mode, prompt, messages, systemMessage, parameters, selectedService);

  useEffect(() => {
    if (open && codeRef.current) {
      Prism.highlightElement(codeRef.current);
    }
  }, [open, selectedIndex, code]);

  const handleCopy = () => {
    const code = languages[selectedIndex].generate(mode, prompt, messages, systemMessage, parameters, selectedService);
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
                      {languages.map((lang, index) => (
                        <TabPanel key={lang.name}>
                          <div className="relative">
                            <pre className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-auto text-xs font-mono">
                              <code
                                ref={index === selectedIndex ? codeRef : null}
                                className={`language-${lang.prismLang}`}
                              >
                                {lang.generate(mode, prompt, messages, systemMessage, parameters, selectedService)}
                              </code>
                            </pre>
                          </div>
                        </TabPanel>
                      ))}
                    </TabPanels>
                  </TabGroup>
                </div>

                {/* Footer */}
                <div className="flex justify-end px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-b-lg">
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="inline-flex items-center gap-2 rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                  >
                    {copied ? (
                      <>
                        <CheckIcon className="h-4 w-4" />
                        Copied
                      </>
                    ) : (
                      <>
                        <ClipboardDocumentIcon className="h-4 w-4" />
                        Copy
                      </>
                    )}
                  </button>
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
  prompt: PropTypes.string,
  messages: PropTypes.array,
  systemMessage: PropTypes.object,
  parameters: PropTypes.object,
};

export default CodeSnippetModal;
