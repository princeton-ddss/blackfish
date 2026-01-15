import { expect, jest, test, it } from '@jest/globals';
import {
  sleep,
  appendBasePath,
  classNames,
  randomInt,
  isDeepEmpty,
  getUniqueRepoIds,
  ServiceStatus,
  fileSize,
  lastModified,
  formattedTimeInterval,
  isServiceRunning
} from "@/app/lib/util";

describe("Utils", () => {
  test("sleep", () => {
    return expect(sleep(4)).resolves.toBeGreaterThan(0);
  });

  test("appendBasePath", () => {
    expect(appendBasePath("test-path")).toBe("test-path");
    expect(typeof appendBasePath("test-path")).toBe("string");
    process.env.basePath = "/base-path/";
    expect(appendBasePath("test-path")).toBe("/base-path/test-path");
    expect(typeof appendBasePath("test-path")).toBe("string");
  });

  test("classNames", () => {
    expect(
      classNames(
        "one",
        "two-words",
        null,
        undefined,
        NaN,
        false,
        true,
        {},
        [],
        99,
        0,
        -200,
        -0,
        1.55,
        -4.2,
        1_0000,
        "spaced words"
      )
    ).toBe("one two-words true [object Object]  99 -200 1.55 -4.2 10000 spaced words");
  });

  test("ServiceStatus", () => {
    expect(Object.isFrozen(ServiceStatus)).toBeTruthy();
    expect(ServiceStatus.SUBMITTED).toBe("submitted");
    expect(ServiceStatus.PENDING).toBe("pending");
    expect(ServiceStatus.STARTING).toBe("starting");
    expect(ServiceStatus.HEALTHY).toBe("healthy");
    expect(ServiceStatus.UNHEALTHY).toBe("unhealthy");
    expect(ServiceStatus.TIMEOUT).toBe("timeout");
    expect(ServiceStatus.STOPPED).toBe("stopped");
    expect(ServiceStatus.EXPIRED).toBe("expired");
    expect(ServiceStatus.FAILED).toBe("failed");
  });

  test("getUniqueRepoIds", () => {
    const unique_repo_ids = getUniqueRepoIds([
      {repo_id: "1234567890"},
      {repo_id: "1234567890"},
      {repo_id: "0987654321"},
      {repo_id: "0987654321"},
    ]);
    expect(unique_repo_ids).toHaveLength(2);
    expect(unique_repo_ids).toStrictEqual([
      {repo_id: "1234567890"},
      {repo_id: "0987654321"},
    ]);
    expect(getUniqueRepoIds([])).toHaveLength(0);
    expect(getUniqueRepoIds([])).toStrictEqual([]);
  });

  test("fileSize", () => {
    expect(fileSize(0)).toBe("0 B");
    expect(fileSize(100)).toBe("100 B");
    expect(fileSize(1000)).toBe("1 KB");
    expect(fileSize(1_000_000)).toBe("1 MB");
    expect(fileSize(1_000_000_000)).toBe("1 GB");
    expect(fileSize(1_000_000_000_000)).toBe("1 TB");
    expect(fileSize(1_000_000_000_000_000)).toBe("1000 TB");
    expect(() => fileSize("500")).toThrow(Error);
    expect(() => fileSize(true)).toThrow(Error);
  });

  test("lastModified", () => {
    jest
      .useFakeTimers()
      .setSystemTime(new Date("Wed Jun 04 2025 13:31:35 GMT-0400 (Eastern Daylight Time)"));
    expect(
      lastModified("Wed Jun 04 2025 13:31:00 GMT-0400 (Eastern Daylight Time)")
    ).toBe("35 seconds ago");
    expect(
      lastModified("Wed Jun 04 2025 13:00:00 GMT-0400 (Eastern Daylight Time)")
    ).toBe("31 minutes ago");
    expect(
      lastModified("Wed Jun 02 2025 13:31:00 GMT-0400 (Eastern Daylight Time)")
    ).toBe("2 days ago");
    expect(
      lastModified("Wed Jan 04 2025 13:31:00 GMT-0400 (Eastern Daylight Time)")
    ).toBe("151 days ago");
    expect(() => lastModified("not a date")).toThrow(Error);
    // Test edge cases for different time ranges
    expect(
      lastModified("Wed Jun 04 2025 13:30:35 GMT-0400 (Eastern Daylight Time)")
    ).toBe("1 minutes ago");
    expect(
      lastModified("Wed Jun 04 2025 12:31:35 GMT-0400 (Eastern Daylight Time)")
    ).toBe("1 hours ago");
  });

  test("formattedTimeInterval", () => {
    const baseTime = new Date("2025-06-04T13:00:00.000Z");

    // Seconds only
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:00:30.000Z")))
      .toBe("30 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:00:01.000Z")))
      .toBe("1 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:00:59.000Z")))
      .toBe("59 sec");

    // Minutes and seconds
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:01:00.000Z")))
      .toBe("1 min 0 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:01:30.000Z")))
      .toBe("1 min 30 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:59:45.000Z")))
      .toBe("59 min 45 sec");

    // Hours and minutes
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T14:00:00.000Z")))
      .toBe("1 hr 0 min");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T14:30:15.000Z")))
      .toBe("1 hr 30 min");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T23:45:30.000Z")))
      .toBe("10 hr 45 min");

    // Days and minutes
    expect(formattedTimeInterval(baseTime, new Date("2025-06-05T13:00:00.000Z")))
      .toBe("1 day 0 min");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-05T13:30:00.000Z")))
      .toBe("1 day 30 min");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-07T14:45:00.000Z")))
      .toBe("3 days 45 min");

    // Test absolute value (refTime after currentTime)
    expect(formattedTimeInterval(new Date("2025-06-04T13:01:00.000Z"), baseTime))
      .toBe("1 min 0 sec");
    expect(formattedTimeInterval(new Date("2025-06-04T14:00:00.000Z"), baseTime))
      .toBe("1 hr 0 min");

    // Edge cases
    expect(formattedTimeInterval(baseTime, baseTime)).toBe("0 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:00:00.001Z")))
      .toBe("0 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:00:00.999Z")))
      .toBe("0 sec");

    // Test with milliseconds that don't affect seconds
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:00:01.500Z")))
      .toBe("1 sec");
    expect(formattedTimeInterval(baseTime, new Date("2025-06-04T13:01:30.750Z")))
      .toBe("1 min 30 sec");

    // Large time intervals
    expect(formattedTimeInterval(baseTime, new Date("2025-06-11T13:00:00.000Z")))
      .toBe("7 days 0 min");
    expect(formattedTimeInterval(baseTime, new Date("2025-07-04T15:30:00.000Z")))
      .toBe("30 days 30 min");
  });

  test("IsServiceRunning", () => {
    expect(isServiceRunning()).toBe(false);
    expect(isServiceRunning({})).toBe(false);
    expect(isServiceRunning([])).toBe(false);
    expect(isServiceRunning({status: null})).toBe(false);
    expect(isServiceRunning({status: false})).toBe(false);
    expect(isServiceRunning({status: undefined})).toBe(false);
    expect(isServiceRunning({status: 0})).toBe(false);
    expect(isServiceRunning({status: -2})).toBe(false);
    expect(isServiceRunning({status: 2})).toBe(false);
    expect(isServiceRunning({status: "healthy"})).toBe(true);
    expect(isServiceRunning({status: "unhealthy"})).toBe(true);
    expect(isServiceRunning({status: "starting"})).toBe(false);
    expect(isServiceRunning({status: "pending"})).toBe(false);
    expect(isServiceRunning({status: "submitted"})).toBe(false);
    expect(isServiceRunning({status: "expired"})).toBe(false);
    expect(isServiceRunning({status: "timeout"})).toBe(false);
    expect(isServiceRunning({status: "failed"})).toBe(false);
  });

  describe("randomInt", () => {
    it("returns greater or equal to 0, and less than or equal to 100", () => {
      const smallRandomInt = randomInt();
      expect(smallRandomInt).toBeGreaterThanOrEqual(0);
      expect(smallRandomInt).toBeLessThanOrEqual(100);
    });

    it("returns greater or equal to 10,000, and less than or equal to 21,000", () => {
      const largeRandomInt = randomInt(10_000, 21_000);
      expect(largeRandomInt).toBeGreaterThanOrEqual(10_000);
      expect(largeRandomInt).toBeLessThanOrEqual(21_000);
    });
  });

  describe("isDeepEmpty", () => {
    it("returns true if called with null or undefined", () => {
      expect(isDeepEmpty(null)).toBe(true);
      expect(isDeepEmpty(undefined)).toBe(true);
    });

    it("returns true if called with 0 length iterables", () => {
      expect(isDeepEmpty("")).toBe(true);
      expect(isDeepEmpty({})).toBe(true);
      expect(isDeepEmpty([])).toBe(true);
    });

    it("returns false if called with falsy numbers", () => {
      expect(isDeepEmpty(0)).toBe(false);
      expect(isDeepEmpty(-0)).toBe(false);
    })

    it("returns false if called with shallow truthy values", () => {
      expect(isDeepEmpty(true)).toBe(false);
      expect(isDeepEmpty(6)).toBe(false);
      expect(isDeepEmpty("hello")).toBe(false);
      expect(isDeepEmpty("undefined")).toBe(false);
      expect(isDeepEmpty(["one", "two", "three"])).toBe(false);
      expect(isDeepEmpty({confirm: "yes", deny: "no"})).toBe(false);
    });

    // TODO This *should* return `true`, but achieving would significantly
    // complicate the function.
    it("returns true if called with built-in objects with prototypes", () => {
      expect(isDeepEmpty(new Date("2025-06-25T16:15:58"))).toBe(true);
    });

    it("returns false if called with deep truthy values", () => {
      expect(isDeepEmpty({
        top_prop: 6,
        nested: {
          low_prop: 66,
          deeper: {
            lower_prop: 666
          }
        }
      })).toBe(false);
      expect(isDeepEmpty([
        {prop: "hello", nested: ["one", "two"]},
        {prop: 71, nested: {prop: ""}},
      ])).toBe(false);
    });

    it("returns true if called with deep null values", () => {
      expect(isDeepEmpty({prop: null})).toBe(true);
      expect(isDeepEmpty({
        prop: null,
        deep: {
          nope: null,
          deeper: {
            nothing: null
          }
        }
      })).toBe(true);
    });

    it("returns false if called with deep falsy values", () => {
      expect(isDeepEmpty({
        empty_str: "",
        zero: 0,
        none: false,
        nope: null,
        huh: undefined,
        deep: {
          nothing: false
        }
      })).toBe(false);
    });
  });

  afterAll(() => {
    delete process.env.basePath;
  });
});
