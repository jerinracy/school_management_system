import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Book,
  Plus,
  Search,
  Library,
} from "lucide-react";
import {
  operationsApi,
} from "../api/operationsApi";
import {
  bookSchema,
  type BookFormData,
} from "../schemas/operationsSchemas";

export const LibraryCatalogPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isAddOpen, setIsAddOpen] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch books
  const { data: booksData, isLoading } = useQuery({
    queryKey: ["library-books", searchQuery],
    queryFn: () =>
      operationsApi.getBooks({
        search: searchQuery || undefined,
      }),
  });

  const books = booksData?.results || [];

  // Create book mutation
  const createMutation = useMutation({
    mutationFn: (data: BookFormData) =>
      operationsApi.createBook({
        ...data,
        total_copies: 1,
        available_copies: 1,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["library-books"] });
      setIsAddOpen(false);
      reset();
      setFeedback({ type: "success", message: t("operations.bookAdded", "Book catalogued successfully") });
    },
    onError: (err: Error) => {
      setFeedback({ type: "error", message: err.message });
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<BookFormData>({
    resolver: zodResolver(bookSchema) as never,
    defaultValues: {
      title: "",
      title_bn: "",
      authors: "",
      isbn: "",
      category: "General",
      publisher: "",
      edition: "1st",
      is_reference_only: false,
    },
  });

  const onSubmit = (data: BookFormData) => {
    createMutation.mutate(data);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <Library className="w-7 h-7 text-emerald-600" />
            {t("operations.libraryCatalogTitle", "Library Book Catalog")}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t(
              "operations.libraryCatalogSubtitle",
              "Search titles, manage ISBN records, Dewey call numbers, and track shelf stock availability"
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reset();
            setIsAddOpen(true);
          }}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition"
        >
          <Plus className="w-4 h-4 mr-2" />
          {t("operations.addBook", "Add New Book")}
        </button>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-lg flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          <span className="text-sm font-medium">{feedback.message}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-xs underline hover:no-underline ml-4"
          >
            {t("common.dismiss", "Dismiss")}
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div className="relative w-full sm:max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder={t("operations.searchBooks", "Search by title, ISBN, or author...")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Books Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-gray-500">
            <div className="inline-block animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full mb-3" />
            <p className="text-sm">{t("common.loading", "Loading book catalog...")}</p>
          </div>
        ) : books.length === 0 ? (
          <div className="p-12 text-center">
            <Book className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-base font-medium text-gray-900">
              {t("operations.noBooksFound", "No Books in Catalog")}
            </h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              {t("operations.noBooksDesc", "Add books to catalogue institutional library inventory.")}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 font-medium text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">{t("operations.bookTitle", "Title & Authors")}</th>
                  <th className="px-4 py-3">{t("operations.isbn", "ISBN / Category")}</th>
                  <th className="px-4 py-3">{t("operations.publisher", "Publisher & Edition")}</th>
                  <th className="px-3 py-3 text-center">{t("operations.copies", "Copies (Total/Avail)")}</th>
                  <th className="px-4 py-3">{t("operations.type", "Type")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {books.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50/75 transition">
                    <td className="px-5 py-3">
                      <div className="font-semibold text-gray-900">{b.title}</div>
                      {b.title_bn && <div className="text-xs text-gray-500">{b.title_bn}</div>}
                      <div className="text-xs text-gray-600 mt-0.5">By {b.authors}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="font-mono text-xs font-semibold text-gray-800">
                        {b.isbn || "—"}
                      </div>
                      <div className="text-xs text-gray-500">{b.category || "General"}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                      <div>{b.publisher || "—"}</div>
                      <div className="text-gray-400">{b.edition ? `${b.edition} Edition` : ""}</div>
                    </td>
                    <td className="px-3 py-3 text-center whitespace-nowrap text-xs">
                      <span className="font-bold text-emerald-700">{b.available_copies}</span>
                      <span className="text-gray-400"> / {b.total_copies}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {b.is_reference_only ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                          Reference Only
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                          Circulating
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Book Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl relative animate-in fade-in duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-gray-200">
              <h3 className="text-lg font-bold text-gray-900">
                {t("operations.addNewBookModal", "Catalog New Book")}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="text-gray-400 hover:text-gray-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => {
                void handleSubmit(onSubmit)(e);
              }}
              className="mt-4 space-y-4"
            >
              <div>
                <label htmlFor="book_title" className="block text-xs font-semibold text-gray-700 mb-1">
                  Book Title (English) *
                </label>
                <input
                  id="book_title"
                  type="text"
                  {...register("title")}
                  placeholder="e.g. Higher Secondary Physics Paper I"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.title && <p className="text-xs text-red-600 mt-1">{errors.title.message}</p>}
              </div>

              <div>
                <label htmlFor="book_title_bn" className="block text-xs font-semibold text-gray-700 mb-1">
                  Book Title (বাংলা)
                </label>
                <input
                  id="book_title_bn"
                  type="text"
                  {...register("title_bn")}
                  placeholder="যেমন: উচ্চ মাধ্যমিক পদার্থবিজ্ঞান প্রথম পত্র"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              <div>
                <label htmlFor="book_authors" className="block text-xs font-semibold text-gray-700 mb-1">
                  Author(s) *
                </label>
                <input
                  id="book_authors"
                  type="text"
                  {...register("authors")}
                  placeholder="e.g. Dr. Shahjahan Tapan"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                />
                {errors.authors && <p className="text-xs text-red-600 mt-1">{errors.authors.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="book_isbn" className="block text-xs font-semibold text-gray-700 mb-1">
                    ISBN
                  </label>
                  <input
                    id="book_isbn"
                    type="text"
                    {...register("isbn")}
                    placeholder="978-984-..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label htmlFor="book_category" className="block text-xs font-semibold text-gray-700 mb-1">
                    Category / Genre
                  </label>
                  <input
                    id="book_category"
                    type="text"
                    {...register("category")}
                    placeholder="e.g. Science, Literature, History"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="book_ref_only"
                  {...register("is_reference_only")}
                  className="h-4 w-4 text-emerald-600 focus:ring-emerald-500 border-gray-300 rounded"
                />
                <label htmlFor="book_ref_only" className="ml-2 block text-xs font-medium text-gray-700">
                  Reference Copy Only (Not for home loan)
                </label>
              </div>

              <div className="pt-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || createMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition disabled:opacity-50"
                >
                  {isSubmitting || createMutation.isPending
                    ? t("common.saving", "Saving...")
                    : t("common.create", "Add to Catalog")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default LibraryCatalogPage;
