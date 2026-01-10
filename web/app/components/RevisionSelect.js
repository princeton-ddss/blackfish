"use client";

import { Fragment, useState, useEffect } from "react";
import {
  Field,
  Label,
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
  Transition
} from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";
import { classNames } from "@/app/lib/util";

/**
 * Revision Select component.
 * @param {object} options
 * @param {Array<object>} options.models
 * @param {string} options.models.repo_id
 * @param {string} options.models.revision
 * @param {string} options.repoId
 * @param {Function} options.setModel
 * @param {boolean} options.disabled
 * @return {JSX.Element}
 */
function RevisionSelect({ models, repoId, setModel, disabled }) {

  const [selected, setSelected] = useState(null);

  // filter repo_id revisions
  const revisions = models.filter(model => model.repo_id === repoId);

  // update selection on revisions refresh
  useEffect(() => {
    const revisions = models.filter(model => model.repo_id === repoId);
    if (revisions && revisions.length > 0) {
      setSelected(revisions[0])
    } else {
      setSelected(null)
    }
  }, [models, repoId]);

  // update model on selection
  useEffect(() => {
    if (selected) {
      setModel(selected)
    }
  }, [selected, setModel]);

  // update selection on event
  function handleRevisionChange(value) {
    setSelected(value);
  }

  // handle errors and missingness
  if (selected === null) {
    return <></>;
  }

  return (
    <Field disabled={disabled}>
      <Listbox value={selected} onChange={handleRevisionChange}>
        {({ open }) => (
          <>
            <Label className="block text-sm font-medium leading-6 text-gray-900">
              Revision
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
                    {selected.revision}
                  </span>
                </span>
                {
                  !disabled &&
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
                <ListboxOptions key={selected.revision} className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
                  {revisions.map((model) => (
                    <ListboxOption
                      key={model.revision}
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
                              {model.revision}
                            </span>
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
              </Transition>
            </div>
          </>
        )}
      </Listbox>
    </Field>
  );
}

RevisionSelect.propTypes = {
  models: PropTypes.array,
  repoId: PropTypes.string,
  setModel: PropTypes.func,
  disabled: PropTypes.bool,
};

export default RevisionSelect;
