import { useEffect, useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { blackfishApiURL } from "@/config";
import PropTypes from "prop-types";

/**
 * Single image attachment component with thumbnail preview.
 * @param {object} props
 * @param {object} props.image - The image object with source and file/path info.
 * @param {Function} props.onRemove - Callback to remove this image.
 * @param {Function} props.onError - Callback when image loading fails.
 * @param {number} props.index - Index of this image in the list.
 */
function ImageAttachment({ image, onRemove, onError, index }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false); // TEMP: disabled loading
  const [error, setError] = useState("Not found (404)"); // TEMP: force error
  const [progress, setProgress] = useState(0);
  const [hasContentLength, setHasContentLength] = useState(false);

  useEffect(() => {
    let objectUrl = null;

    const loadImage = async () => {
      setIsLoading(true);
      setError(null);
      setProgress(0);
      setHasContentLength(false);

      try {
        if (image.source === "browser") {
          // Browser file - create object URL
          objectUrl = URL.createObjectURL(image.file);
          setImageUrl(objectUrl);
        } else if (image.source === "remote") {
          // Remote file - fetch via API with progress tracking
          const profileParam =
            image.profile && image.profile.schema !== "local"
              ? `&profile=${encodeURIComponent(image.profile.name)}`
              : "";
          const url = `${blackfishApiURL}/api/image?path=${encodeURIComponent(image.path)}${profileParam}`;

          const response = await fetch(url);
          if (!response.ok) {
            const statusMessages = {
              404: "Not found",
              403: "Access denied",
              500: "Server error",
            };
            throw new Error(statusMessages[response.status] || `Error (${response.status})`);
          }

          const contentLength = response.headers.get("Content-Length");
          if (contentLength && response.body) {
            // Stream with progress tracking
            const total = parseInt(contentLength, 10);
            setHasContentLength(true);
            setProgress(1); // Show determinate bar immediately

            const reader = response.body.getReader();
            const chunks = [];
            let receivedLength = 0;

            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              chunks.push(value);
              receivedLength += value.length;
              setProgress(Math.max(1, Math.round((receivedLength / total) * 100)));
            }

            // Combine chunks into blob
            const blob = new Blob(chunks);
            objectUrl = URL.createObjectURL(blob);
          } else {
            // Fallback if Content-Length not available - use indeterminate progress
            const blob = await response.blob();
            objectUrl = URL.createObjectURL(blob);
          }
          setImageUrl(objectUrl);
        }
      } catch (err) {
        console.error("Failed to load image:", err);
        setError(err.message);
        if (onError) {
          const name = image.source === "browser" ? image.file.name : image.path.split("/").pop();
          onError(name, err.message);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadImage();

    // Cleanup object URL on unmount
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [image, onError]);

  const displayName =
    image.source === "browser"
      ? image.file.name
      : image.path.split("/").pop();

  return (
    <div className="relative group flex-shrink-0">
      <div className="relative w-16 h-16 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 border border-gray-200 dark:border-gray-600">
        {isLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100 dark:bg-gray-700">
            {hasContentLength && progress > 0 ? (
              // Determinate progress bar with percentage (for streaming remote files)
              <>
                <div className="w-10 h-1.5 bg-gray-300 dark:bg-gray-600 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-150"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-[8px] text-gray-500 dark:text-gray-400 mt-1">{progress}%</span>
              </>
            ) : (
              // Spinner for initial loading state
              <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
            )}
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-500">
            <XMarkIcon className="w-6 h-6" />
          </div>
        )}

        {imageUrl && !isLoading && !error && (
          <img
            src={imageUrl}
            alt={displayName}
            className="w-full h-full object-cover"
          />
        )}

        {/* Source indicator */}
        <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[8px] px-1 py-0.5 truncate">
          {image.source === "remote" ? "Remote" : "Local"}
        </div>
      </div>

      {/* Remove button - hidden during loading to prevent race condition */}
      {!isLoading && (
        <button
          type="button"
          onClick={() => onRemove(index)}
          className="absolute -top-2.5 -right-2.5 z-50 w-5 h-5 bg-gray-800 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-900"
          aria-label={`Remove ${displayName}`}
        >
          <XMarkIcon className="w-3 h-3 text-white" />
        </button>
      )}
    </div>
  );
}

ImageAttachment.propTypes = {
  image: PropTypes.shape({
    source: PropTypes.oneOf(["browser", "remote"]).isRequired,
    file: PropTypes.object,
    path: PropTypes.string,
    profile: PropTypes.object,
  }).isRequired,
  onRemove: PropTypes.func.isRequired,
  onError: PropTypes.func,
  index: PropTypes.number.isRequired,
};

export default ImageAttachment;
