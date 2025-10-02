#!/usr/bin/env bb
(ns bump-tag
  (:require [babashka.cli :as cli]
            [babashka.fs :as fs]
            [babashka.process :refer [shell]]
            [cheshire.core :as json]
            [clojure.string :as str]
            [clj-yaml.core :as yaml]))

(def GAR-project-id
  "GAR project name"
  "artifact-registry-5n")

(def GAR-path
  "Path to the GAR onyxia images"
  (str/join "/" ["europe-north1-docker.pkg.dev" GAR-project-id "dapla-lab-docker/onyxia/"]))

(defn fetch-artifact-tags
  "Fetch list of sorted docker tags for a given artifact."
  [artifact]
  (as-> (str GAR-path artifact) arg
    (shell {:out :string} "gcloud" "artifacts" "docker" "tags" "list" arg
           "--sort-by=tag" "--format=json(tag)")
    (:out arg)
    (json/parse-string arg true)
    (map :tag arg)))

(defn extract-tags [splitter tags]
  (->> tags
       (partition-by #(str/includes? % splitter))
       (map last)))

(def artifact->splitter
  "Map of artifact names and their tag splitters"
  {"jupyter" "py312"
   "jupyter-playground" "py312"
   "jupyter-pyspark" "py312"
   "vscode-python" "py312"
   "rstudio" "r4.4.0"})

(defn process-tags [artifact]
  (shell "gcloud" "config" "set" "project" GAR-project-id) ; ensure we're in the GAR project
  (->> (fetch-artifact-tags artifact)
       ((if-let [splitter (artifact->splitter artifact)]
          (partial extract-tags splitter)
          (partial take-last 2)))
       (map #(-> %
                 (str/last-index-of "/")
                 inc
                 (drop %)
                 str/join))
       (interleave [:default :secondary])
       (apply hash-map)))

(def yaml-encoding-options
  {:dumper-options {:flow-style :block
                    :indicator-indent 2
                    :indent-with-indicator true}})

(defn update-helm-chart-values
  "Update image tags in values yaml and schema files."
  [chart-dir]
  (let [schema-filepath (str chart-dir "/values.schema.json")
        values-filepath (str chart-dir "/values.yaml")
        values-schema (json/parse-string (slurp schema-filepath) true)
        values (yaml/parse-string (slurp values-filepath))
        artifact (str/replace-first chart-dir #"./charts/" "")
        {:keys [default secondary]} (process-tags artifact)
        updated-values-schema
        (-> values-schema
            (update-in [:properties :tjeneste :properties :version :default] (constantly default))
            (update-in [:properties :tjeneste :properties :version :listEnum] (constantly [default secondary])))
        updated-values (update-in values [:tjeneste :version] (constantly default))]
    (spit schema-filepath (json/generate-string updated-values-schema {:pretty true}))
    (spit values-filepath (yaml/generate-string updated-values yaml-encoding-options))))

(defn bump-helm-chart-version
  "Bump the patch version of the helm chart."
  [chart-dir]
  (let [filepath (str chart-dir "/Chart.yaml")
        chart (yaml/parse-string (slurp filepath))
        semver (:version chart)
        new-version
        (if-let [[_ major minor patch] (re-matches #"^(\d+)\.(\d+)\.(\d+)" semver)]
          (str major "." minor "." (inc (Integer/parseInt patch)))
          (throw (ex-info "Invalid SemVer string" {:semver semver})))
        new-chart (update-in chart [:version] (constantly new-version))]
    (spit filepath
          (yaml/generate-string
           new-chart
           yaml-encoding-options))))

(defn update-helm-chart-tag
  "Update entire helm chart with new image tag."
  [chart-dir]
  (update-helm-chart-values chart-dir)
  (bump-helm-chart-version chart-dir))

(def all-charts "List of all helm charts." (conj (keys artifact->splitter) "jdemetra"))

(defn update-helm-charts-tag
  "Update the image tag of given helm charts."
  [helm-charts]
  (->> helm-charts
       (map (partial str "./charts/"))
       (pmap update-helm-chart-tag)
       doall))

(defn show-help
  "Show CLI help string."
  [spec]
  (cli/format-opts
   (merge spec {:order (vec (keys (:spec spec)))})))

(def cli-spec
  "The specification for supported CLI arguments"
  {:spec {:all {:coerce :boolean
                :desc "Target all helm charts"}}
   :error-fn
   (fn [{:keys [type cause msg option]}]
     (when (= :org.babashka/cli type)
       (case cause
         :require
         (println
          (format "Missing required argument: %s\n" option))
         :validate
         (println
          (format "%s does not exist!\n" msg)))))})

(defn -main "Script entrypoint." [& raw-args]
  (let [{:keys [args opts]} (cli/parse-args raw-args cli-spec)
        chart-dir (first args)]
    (cond
      (or (:help opts) (:h opts))
      (println
       (str/join "\n\n"
                 ["Bump the helm chart image tag."
                  "Usage: bump_tag.clj HELM-CHART-PATH"
                  "Flags:"
                  (show-help cli-spec)]))
      (:all opts) (do
                    (update-helm-charts-tag all-charts)
                    (println "Updated helm charts:" (str/join ", " all-charts)))
      chart-dir
      (if (fs/directory? chart-dir)
        (update-helm-chart-tag chart-dir)
        (println (format "The directory %s does not exist." chart-dir)))
      :else (println "No arguments passed... exiting script."))))

(when (= *file* (System/getProperty "babashka.file"))
  (apply -main *command-line-args*))
