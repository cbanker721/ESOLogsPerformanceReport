(function () {
  function formatTimestamp(ms) {
    if (!ms || Number.isNaN(Number(ms))) {
      return "-";
    }
    const d = new Date(Number(ms));
    if (Number.isNaN(d.getTime())) {
      return "-";
    }
    return d.toLocaleString();
  }

  function textOrDash(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }
    return String(value);
  }

  function pickLabel(obj) {
    if (!obj || typeof obj !== "object") {
      return "-";
    }

    if (obj.name) {
      return String(obj.name);
    }

    if (obj.slug) {
      return String(obj.slug);
    }

    if (obj.code) {
      return String(obj.code);
    }

    if (obj.id !== undefined && obj.id !== null) {
      return String(obj.id);
    }

    return "-";
  }

  function reportSummaryFromApi(raw) {
    const code = raw && raw.code ? String(raw.code) : "";
    return {
      code,
      title: textOrDash(raw ? raw.title : null),
      startTime: raw ? raw.startTime : null,
      endTime: raw ? raw.endTime : null,
      startTimeText: formatTimestamp(raw ? raw.startTime : null),
      endTimeText: formatTimestamp(raw ? raw.endTime : null),
      externalReportUrl: code ? "https://www.esologs.com/reports/" + encodeURIComponent(code) : "",
      localReportUrl: code ? "./report.html?code=" + encodeURIComponent(code) : ""
    };
  }

  function reportListFromApi(block) {
    const rows = Array.isArray(block && block.data) ? block.data : [];
    return {
      total: block ? block.total : null,
      currentPage: block ? block.current_page : null,
      perPage: block ? block.per_page : null,
      hasMorePages: Boolean(block && block.has_more_pages),
      reports: rows.map(reportSummaryFromApi)
    };
  }

  function reportMetadataFromApi(raw) {
    const code = raw && raw.code ? String(raw.code) : "";
    const archiveStatus = raw && raw.archiveStatus ? raw.archiveStatus : null;

    return {
      code,
      title: textOrDash(raw ? raw.title : null),
      startTime: raw ? raw.startTime : null,
      endTime: raw ? raw.endTime : null,
      startTimeText: formatTimestamp(raw ? raw.startTime : null),
      endTimeText: formatTimestamp(raw ? raw.endTime : null),
      visibility: textOrDash(raw ? raw.visibility : null),
      revision: textOrDash(raw ? raw.revision : null),
      segments: textOrDash(raw ? raw.segments : null),
      exportedSegments: textOrDash(raw ? raw.exportedSegments : null),
      region: pickLabel(raw ? raw.region : null),
      zone: pickLabel(raw ? raw.zone : null),
      owner: pickLabel(raw ? raw.owner : null),
      guild: pickLabel(raw ? raw.guild : null),
      guildTag: pickLabel(raw ? raw.guildTag : null),
      archived: archiveStatus && typeof archiveStatus.isArchived !== "undefined"
        ? String(Boolean(archiveStatus.isArchived))
        : "-",
      archiveAccessible: archiveStatus && typeof archiveStatus.isAccessible !== "undefined"
        ? String(Boolean(archiveStatus.isAccessible))
        : "-",
      archiveDate: archiveStatus && archiveStatus.archiveDate
        ? formatTimestamp(Number(archiveStatus.archiveDate) * 1000)
        : "-",
      externalReportUrl: code ? "https://www.esologs.com/reports/" + encodeURIComponent(code) : ""
    };
  }

  function formatDurationMs(ms) {
    if (!Number.isFinite(ms) || ms < 0) {
      return "-";
    }

    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
  }

  function reportFightFromApi(raw, reportStartTime) {
    const relStart = Number(raw && raw.startTime ? raw.startTime : 0);
    const relEnd = Number(raw && raw.endTime ? raw.endTime : 0);
    const hasReportStart = Number.isFinite(Number(reportStartTime));
    const absStart = hasReportStart ? Number(reportStartTime) + relStart : null;
    const absEnd = hasReportStart ? Number(reportStartTime) + relEnd : null;

    const difficulty = raw && raw.difficulty !== undefined && raw.difficulty !== null
      ? Number(raw.difficulty)
      : null;
    const fightType = classifyFightType(difficulty);

    return {
      id: raw && raw.id !== undefined ? String(raw.id) : "-",
      name: textOrDash(raw ? raw.name : null),
      encounterID: raw && raw.encounterID !== undefined ? String(raw.encounterID) : "-",
      difficulty: difficulty !== null && Number.isFinite(difficulty) ? String(difficulty) : "-",
      kill: raw && typeof raw.kill !== "undefined" ? String(Boolean(raw.kill)) : "-",
      startTimeText: absStart ? formatTimestamp(absStart) : "-",
      endTimeText: absEnd ? formatTimestamp(absEnd) : "-",
      durationText: formatDurationMs(relEnd - relStart),
      fightType
    };
  }

  function classifyFightType(difficulty) {
    if (difficulty === 122) {
      return "Hard Mode";
    }

    if (difficulty === 121) {
      return "Veteran";
    }

    return "Trash";
  }

  function reportFightsFromApi(rawFights, reportStartTime) {
    const rows = Array.isArray(rawFights) ? rawFights : [];
    return rows.map((f) => reportFightFromApi(f, reportStartTime));
  }

  function segregateFights(fights) {
    const rows = Array.isArray(fights) ? fights : [];
    const grouped = {
      veteranOrHardMode: [],
      trash: []
    };

    for (const fight of rows) {
      if (fight.fightType === "Veteran" || fight.fightType === "Hard Mode") {
        grouped.veteranOrHardMode.push(fight);
      } else {
        grouped.trash.push(fight);
      }
    }

    return grouped;
  }

  function groupFightsByEncounterId(fights) {
    const rows = Array.isArray(fights) ? fights : [];
    const order = [];
    const map = Object.create(null);

    for (const fight of rows) {
      const encounterID = fight && fight.encounterID ? String(fight.encounterID) : "-";
      if (!map[encounterID]) {
        map[encounterID] = [];
        order.push(encounterID);
      }
      map[encounterID].push(fight);
    }

    return order.map((encounterID) => ({
      encounterID,
      fights: map[encounterID]
    }));
  }

  function groupFightsByEncounterThenDifficulty(fights) {
    const encounterGroups = groupFightsByEncounterId(fights);

    return encounterGroups.map((encounterGroup) => {
      const difficultyOrder = [];
      const difficultyMap = Object.create(null);

      for (const fight of encounterGroup.fights) {
        const difficulty = fight && fight.difficulty ? String(fight.difficulty) : "-";
        if (!difficultyMap[difficulty]) {
          difficultyMap[difficulty] = [];
          difficultyOrder.push(difficulty);
        }
        difficultyMap[difficulty].push(fight);
      }

      return {
        encounterID: encounterGroup.encounterID,
        total: encounterGroup.fights.length,
        difficultyGroups: difficultyOrder.map((difficulty) => ({
          difficulty,
          fights: difficultyMap[difficulty]
        }))
      };
    });
  }

  window.ESOLogsDomain = {
    formatTimestamp,
    reportSummaryFromApi,
    reportListFromApi,
    reportMetadataFromApi,
    reportFightFromApi,
    reportFightsFromApi,
    classifyFightType,
    segregateFights,
    groupFightsByEncounterId,
    groupFightsByEncounterThenDifficulty
  };
})();
