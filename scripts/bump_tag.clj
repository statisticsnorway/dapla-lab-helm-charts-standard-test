#!/usr/bin/env bb
(ns bump-tag
  (:require [babashka.cli :as cli]
            [babashka.fs :as fs]
            [babashka.http-client :as http]
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

(defn strip-gar-path "Strip the GAR prefix from a tag." [tag]
  (str/replace tag #".*/" ""))

(defn extract-dep-version "Extract the dependency versions from a tag." [full-tag]
  (-> full-tag
      strip-gar-path
      (str/replace #"-\d{4}\.\d{2}\.\d{2}T\d{2}_\d{2}Z$" "")))

(def artifact->tags
  "Map of artifact names and their tags. Where the first one is the default selection."
  (let [r-and-python-tags ["r4.4.0-py311" "r4.4.0-py312"]]
    {"jdemetra" ["jd2.2.5" "jd3.2.4"]
     "jupyter" r-and-python-tags
     "jupyter-playground" r-and-python-tags
     "jupyter-pyspark" ["py311-spark3.5.3" "py312-spark3.5.3"]
     "vscode-python" r-and-python-tags
     "rstudio" ["r4.3.3" "r4.4.0"]}))

(defn process-tags [artifact]
  (shell "gcloud" "config" "set" "project" GAR-project-id) ; ensure we're in the GAR project
  (->> (fetch-artifact-tags artifact)
       (filter (fn [gar-tag] (some #(str/includes? gar-tag %) (artifact->tags artifact)))) ; for legacy reasons we need to filter on the tag shape
       (partition-by extract-dep-version)
       (map (comp strip-gar-path last))
       (interleave [:default :secondary])
       (apply hash-map)))

(def yaml-encoding-options
  {:dumper-options {:flow-style :block
                    :indicator-indent 2
                    :indent-with-indicator true}})

(defn update-helm-chart-values
  "Update image tags in values yaml and schema files."
  [chart-dir]
  (let [schema-filepath (str (fs/path chart-dir "values.schema.json"))
        values-filepath (str (fs/path chart-dir "values.yaml"))
        values-schema (yaml/parse-string (slurp schema-filepath)) ; read json using yaml decoder to preserve key order
        values (yaml/parse-string (slurp values-filepath))
        artifact (str (.getFileName (fs/path chart-dir)))
        {:keys [default secondary]} (process-tags artifact)
        updated-values-schema
        (-> values-schema
            (update-in [:properties :tjeneste :properties :version :default] (constantly default))
            (update-in [:properties :tjeneste :properties :version :listEnum] (constantly [default secondary])))
        updated-values (update-in values [:tjeneste :version] (constantly default))]
    (spit schema-filepath (json/encode updated-values-schema {:pretty true}))
    (spit values-filepath (yaml/generate-string updated-values yaml-encoding-options))))

(defn bump-helm-chart-version
  "Bump the patch version of the helm chart."
  [chart-dir]
  (let [filepath (str (fs/path chart-dir "Chart.yaml"))
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

(defn bump-library-chart-version
  "Bump the library-chart dependency version of the helm chart."
  [chart-dir]
  (let [filepath (str (fs/path chart-dir "Chart.yaml"))
        chart (yaml/parse-string (slurp filepath))]
    ; Check if helm chart has a dependency on 'library-chart'
    (when (seq (keep (fn [dep] (when (= "library-chart" (:name dep)) dep)) (:dependencies chart)))
      (let [latest-library-chart-version
            (-> "https://api.github.com/repos/statisticsnorway/dapla-lab-helm-charts-library/releases/latest"
                http/get
                :body
                (json/decode true)
                :name
                (#(re-find #"\d+.\d+.\d+" %)))
            new-chart (update-in chart [:dependencies]
                                 (fn [deps]
                                   (mapv #(if (= "library-chart" (:name %))
                                            (assoc-in % [:version] latest-library-chart-version)
                                            %) deps)))]
        (spit filepath
              (yaml/generate-string
               new-chart
               yaml-encoding-options))))))

(defn update-helm-chart-deps
  "Update helm chart with new dependency tag."
  [chart-dir]
  (bump-library-chart-version chart-dir)
  (bump-helm-chart-version chart-dir))

(defn update-helm-chart-tag
  "Update entire helm chart with new image tag."
  [chart-dir]
  (update-helm-chart-values chart-dir)
  (bump-helm-chart-version chart-dir))

(def all-charts "List of all helm charts."
  (map #(str "./charts/" %) (keys artifact->tags)))

(defn update-helm-charts-deps
  "Update the dependencies of given helm charts."
  [helm-charts]
  (->> helm-charts
       (pmap update-helm-chart-deps)
       doall))

(defn update-helm-charts-tag
  "Update the image tag of given helm charts."
  [helm-charts]
  (->> helm-charts
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
                :desc "Target all helm charts"}
          :deps {:coerce :boolean
                 :desc "Update helm chart dependencies"}}
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
  (let [{:keys [args opts]} (cli/parse-args raw-args cli-spec)]
    (cond
      (some opts [:help :h])
      (println
       (str/join "\n\n"
                 ["Bump the helm chart image tag."
                  "Usage: bump_tag.clj HELM-CHART-PATH..."
                  "Flags:"
                  (show-help cli-spec)]))
      (every? opts [:all :deps]) (do
                                   (update-helm-charts-deps all-charts)
                                   (println "Updated helm charts deps:" (str/join ", " all-charts)))
      (:all opts) (do
                    (update-helm-charts-tag all-charts)
                    (println "Updated helm charts:" (str/join ", " all-charts)))
      (and (:deps opts) (every? fs/directory? args)) (update-helm-charts-deps args)
      args
      (if (every? fs/directory? args)
        (update-helm-charts-tag args)
        (println (format "The directory %s does not exist." (some #(when-not (fs/directory? %) %) args))))
      :else (println "No arguments passed... exiting script."))))

(when (= *file* (System/getProperty "babashka.file"))
  (apply -main *command-line-args*))
