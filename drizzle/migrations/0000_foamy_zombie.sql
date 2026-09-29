CREATE TABLE "datasets" (
	"id" serial PRIMARY KEY NOT NULL,
	"source_label" text NOT NULL,
	"uploaded_at" timestamp with time zone DEFAULT now() NOT NULL,
	"sku_count" integer NOT NULL,
	"rejected_row_count" integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE "sku_records" (
	"id" serial PRIMARY KEY NOT NULL,
	"dataset_id" integer NOT NULL,
	"sku" text NOT NULL,
	"product_name" text NOT NULL,
	"category" text NOT NULL,
	"size" text NOT NULL,
	"color" text NOT NULL,
	"quantity_on_hand" integer NOT NULL,
	"reorder_point" integer NOT NULL,
	"cost_per_unit" numeric NOT NULL,
	"retail_price" numeric NOT NULL,
	"last_restock_date" text NOT NULL,
	"units_sold_30d" integer NOT NULL,
	"supplier" text NOT NULL,
	"season" text NOT NULL,
	"inventory_value" numeric NOT NULL,
	"revenue_30d" numeric NOT NULL,
	"gross_margin_30d" numeric NOT NULL,
	"itr_annualised" numeric NOT NULL,
	"days_of_stock" numeric NOT NULL,
	"fsn_class" text NOT NULL,
	"abc_class" text NOT NULL,
	"abc_revenue_share" numeric NOT NULL,
	"abc_cumulative_share" numeric NOT NULL,
	"stock_status" text NOT NULL,
	"priority_tag" text NOT NULL
);
--> statement-breakpoint
ALTER TABLE "sku_records" ADD CONSTRAINT "sku_records_dataset_id_datasets_id_fk" FOREIGN KEY ("dataset_id") REFERENCES "public"."datasets"("id") ON DELETE cascade ON UPDATE no action;