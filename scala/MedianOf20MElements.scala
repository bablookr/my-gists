package com.example

import org.apache.spark.sql.SparkSession

import java.nio.file.{Files, Paths}
import java.util.Random

/**
 * Problem:
 * 
 * Find the median of a large array of elements distributed across multiple nodes 
 * given that it's not possible to collect all the elements in a single node.
 * 
 * Solution:
 * 
 * This class is used to find the median of 20 million elements distributed across 4 files.
 * It uses spark to read the files, merge them, sort the elements and then find the median.
 *
 * As the class has limited error handling, it is assumed that the input files are present and
 * the data in the files is valid.
 *
 * The main method simulates the same by generating 4 files with 5 million elements each and
 * then finding the median using the RDD logic in the class.
 */

class MedianOf20MElements(filePaths: Array[String]) {

  def compute(): Double = {
    val startTime = System.currentTimeMillis()
    val spark = SparkSession.builder().master("local[*]").getOrCreate()

    try {
      val rdd1 = spark.read.text(filePaths(0)).rdd
      val rdd2 = spark.read.text(filePaths(1)).rdd
      val rdd3 = spark.read.text(filePaths(2)).rdd
      val rdd4 = spark.read.text(filePaths(3)).rdd

      val rdd = rdd1
        .union(rdd2)
        .union(rdd3)
        .union(rdd4)
        .map(row => row.getString(0).toInt)
        .sortBy(x => x)
        .zipWithIndex()

      val count = rdd.count()
      val countBy2 = count / 2

      val median = if (count % 2 == 0) {
        val first = rdd.filter(x => x._2 == countBy2 - 1).first()._1
        val second = rdd.filter(x => x._2 == countBy2).first()._1
        (first + second) / 2.0
      } else {
        rdd.filter(x => x._2 == countBy2).first()._1
      }

      median
    } catch {
      case e: Exception =>
        println(s"An error occurred while finding the median: ${e.getMessage}")
        throw e
    } finally {
      println(s"Time taken to find the Median = ${System.currentTimeMillis() - startTime}")
      spark.stop()
    }
  }
}

object MedianOf20MElements {
  val ONE_MILLION = 1000000

  def main(args: Array[String]): Unit = {
    val filePaths = Array("data1.txt", "data2.txt", "data3.txt", "data4.txt")

    generateData(filePaths(0), numLines = 5 * ONE_MILLION, seed = 42)
    generateData(filePaths(1), numLines = 5 * ONE_MILLION, seed = 43)
    generateData(filePaths(2), numLines = 5 * ONE_MILLION, seed = 44)
    generateData(filePaths(3), numLines = 5 * ONE_MILLION, seed = 45)

    println(s"Median = ${new MedianOf20MElements(filePaths).compute()}")
  }

  def generateData(filePath: String,
                   lowerBound: Int = -ONE_MILLION,
                   upperBound: Int = ONE_MILLION,
                   numLines: Int,
                   seed: Long): Unit = {
    val random: Random = new Random(seed)
    val writer = Files.newBufferedWriter(Paths.get(filePath))
    try {
      for (i <- 1 to numLines) {
        val line = (lowerBound + random.nextInt(upperBound - lowerBound + 1)).toString
        writer.write(line)
        writer.newLine()
      }
    } catch {
      case e: Exception =>
        println(s"An error occurred while generating $filePath: ${e.getMessage}")
        throw e
    } finally {
      writer.close()
    }
  }
}
