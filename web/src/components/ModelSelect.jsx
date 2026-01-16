import { Fragment, useEffect, useState } from "react";
import { Field,
  Label,
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
  Transition
} from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";
import { classNames, getUniqueRepoIds } from "@/lib/util";

/**
 * Model Select component.
 * @param {object} options
 * @param {Function} options.setRepoId
 * @param {boolean} options.disabled
 * @return {JSX.Element}
 */
function ModelSelect({ models, setRepoId, disabled }) {

  const [selected, setSelected] = useState(null);

  // filter unique repo_ids
  const repos = getUniqueRepoIds(models);

  // update repo_id on selection
  useEffect(() => {
    if (selected) {
      setRepoId(selected.repo_id);
    }
  }, [selected, setRepoId]);

  // update selection on models refresh
  useEffect(() => {
    if (models && models.length > 0) {
      setSelected(models[0]); // models[0] == repos[0] by definition
    } else {
      setSelected(null);
    }
  }, [models]);

  // update selection on event
  function handleRepoChange(value) {
    setSelected(value);
  }

  // handle errors and missingness
  if (selected === null) {
    return <></>;
  }

  return (
    <Field disabled={disabled}>
      <Listbox value={selected} onChange={handleRepoChange}>
        {({ open }) => (
          <>
            <Label className="block text-sm font-medium leading-6 text-gray-900">
              Model
            </Label>
            <div className="relative mt-2">
              <ListboxButton
                className={classNames(
                  disabled ? "bg-gray-100 ring-gray-300 ring-1" : "bg-white focus:outline-none focus:ring-2 focus:ring-blue-500",
                  "relative w-full cursor-default rounded-md py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 sm:text-sm sm:leading-6"
                )}
              >
                <span className="flex items-center">
                  <span className="ml-2 mr-2 block truncate">
                    {selected.repo_id}
                  </span>
                </span>
                {!disabled &&
                  <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                    <ChevronUpDownIcon
                      className="h-5 w-5 text-gray-400"
                      aria-hidden="true"
                    />
                  </span>
                }
              </ListboxButton>

              <Transition
                show={open}
                as={Fragment}
                leave="transition ease-in duration-100"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                  {repos.map((model) => (
                    <ListboxOption
                      key={model.revision} // revision is unique per profile
                      className={({ focus }) =>
                        classNames(
                          focus ? "bg-blue-500 text-white" : "text-gray-900",
                          "relative cursor-default select-none py-2 pl-1 pr-9"
                        )
                      }
                      value={model}
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
                              {model.repo_id}
                            </span>
                          </div>

                          {selected ? (
                            <span
                              className={classNames(
                                focus ? "text-white" : "text-blue-600",
                                "check-icon absolute inset-y-0 right-0 flex items-center pr-4"
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
              </Transition>
            </div>
          </>
        )}
      </Listbox>
    </Field>
  );
}

ModelSelect.propTypes = {
  models: PropTypes.array,
  setRepoId: PropTypes.func,
  disabled: PropTypes.bool,
};

export default ModelSelect;
