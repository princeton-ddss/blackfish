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
  // Only what the user explicitly picked. The effective selection is derived
  // below rather than stored, so a container change (new profile or service)
  // can never leave a stale tag paired with a new repo.
  const [chosen, setChosen] = useState(null);
  const tags = container?.tags ?? [];
  const isDisabled = disabled || isLoading || tags.length < 2;

  // Prefer the configured default, falling back to the first staged tag when
  // that default is not on disk. A user's pick wins, but only while it is
  // still offered — switching containers drops it.
  const selected = container
    ? (tags.includes(chosen) ? chosen : null) ??
      (container.default_staged ? container.default : tags[0] ?? null)
    : null;

  // Forget the explicit pick when the container changes, so the derived
  // default applies to the new service rather than a tag from the old one.
  useEffect(() => {
    setChosen(null);
  }, [container]);

  // Lift the full "repo:tag" — image_ref stores a complete reference, since a
  // pin may move repos and not just tags. Derived from `container` in the same
  // pass as `selected`, so the two are always consistent.
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
  // the backend resolve its default. A single staged version still renders
  // (disabled) so the user sees which image is going to run.
  if (selected === null) {
    return <></>;
  }

  return (
    <Field disabled={isDisabled}>
      <Listbox value={selected} onChange={setChosen} disabled={isDisabled}>
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
