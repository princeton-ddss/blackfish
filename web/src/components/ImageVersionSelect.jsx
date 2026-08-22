import { useState, useEffect } from "react";
import {
  Field,
  Label,
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";
import { classNames } from "@/lib/util";
import SelectSkeleton from "@/components/SelectSkeleton";

/**
 * Container image version select.
 *
 * Offers only the versions actually staged on the profile, so a selection can
 * always run. Pre-selects the *configured* default rather than the newest
 * staged tag: the pre-selection must only change when someone deliberately
 * changes configuration, not because an administrator staged a new image.
 *
 * Renders nothing when no version is available at all — the profile is
 * unreachable, or discovery failed. The launch then proceeds on the backend's
 * own default, so a flaky login node never blocks it.
 *
 * @param {object} options
 * @param {object} options.container `{repo, tags, default, default_staged}`
 * @param {string} options.imageRef the selected "repo:tag", or null
 * @param {Function} options.setImageRef
 * @param {boolean} options.disabled
 * @param {boolean} options.isLoading
 * @return {JSX.Element}
 */
function ImageVersionSelect({
  container,
  imageRef,
  setImageRef,
  disabled,
  isLoading = false,
}) {
  const [selected, setSelected] = useState(null);
  const isDisabled = disabled || isLoading;

  const tags = container?.tags ?? [];

  // Seed from the configured default whenever the container changes (a new
  // profile or service), falling back to the first staged tag when that
  // default is not on disk.
  useEffect(() => {
    if (!container) {
      setSelected(null);
      return;
    }
    const fallback = container.tags?.[0] ?? null;
    setSelected(container.default_staged ? container.default : fallback);
  }, [container]);

  // Lift the full "repo:tag" — image_ref stores a complete reference, since a
  // pin may move repos and not just tags.
  useEffect(() => {
    if (!setImageRef) return;
    if (selected && container?.repo) {
      setImageRef(`${container.repo}:${selected}`);
    } else {
      setImageRef(null);
    }
  }, [selected, container, setImageRef]);

  if (isLoading) {
    return <SelectSkeleton label="Version" />;
  }

  // Nothing staged, or the profile is unreachable: stay out of the way and let
  // the backend resolve its default. A single staged version still renders, to
  // match RevisionSelect — disabling one-option selects is tracked in #489.
  if (selected === null) {
    return <></>;
  }

  return (
    <Field disabled={isDisabled}>
      <Listbox value={selected} onChange={setSelected} disabled={isDisabled}>
        <Label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100">
          Version
        </Label>
        <div className="relative mt-2">
          <ListboxButton
            className={classNames(
              isDisabled ? "bg-gray-100 dark:bg-gray-800 ring-gray-300 dark:ring-gray-600 ring-1" : "bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500",
              "relative w-full cursor-default rounded-md py-1.5 pl-1 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 sm:text-sm sm:leading-6"
            )}
          >
            <span className="flex items-center">
              <span className="ml-2 mr-2 block truncate" title={imageRef ?? undefined}>
                {selected}
              </span>
            </span>
            {!isDisabled &&
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
              </span>
            }
          </ListboxButton>

          <ListboxOptions
            anchor="bottom start"
            className="z-50 mt-1 max-h-60 w-[var(--button-width)] overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none sm:text-sm">
            {tags.map((tag) => (
              <ListboxOption
                key={tag}
                className={({ focus }) =>
                  classNames(
                    focus ? "bg-blue-500 text-white" : "text-gray-900 dark:text-gray-100",
                    "relative cursor-default select-none py-2 pl-1 pr-9"
                  )
                }
                value={tag}
              >
                {({ selected, focus }) => (
                  <>
                    <div className="flex items-center">
                      <span
                        className={classNames(
                          selected ? "font-semibold" : "font-normal",
                          "ml-3 block truncate"
                        )}
                      >
                        {tag}
                      </span>
                      {tag === container.default && (
                        <span
                          className={classNames(
                            focus ? "text-white" : "text-gray-500 dark:text-gray-400",
                            "ml-2 text-xs"
                          )}
                        >
                          default
                        </span>
                      )}
                    </div>

                    {selected ? (
                      <span
                        className={classNames(
                          focus ? "text-white" : "text-blue-600",
                          "absolute inset-y-0 right-0 flex items-center pr-4"
                        )}
                      >
                        <CheckIcon className="h-5 w-5" aria-hidden="true" />
                      </span>
                    ) : null}
                  </>
                )}
              </ListboxOption>
            ))}
          </ListboxOptions>
        </div>
      </Listbox>
    </Field>
  );
}

ImageVersionSelect.propTypes = {
  container: PropTypes.object,
  imageRef: PropTypes.string,
  setImageRef: PropTypes.func,
  disabled: PropTypes.bool,
  isLoading: PropTypes.bool,
};

export default ImageVersionSelect;
